"""ReportLab-based PDF report generator.

Generates professional, publication-quality financial and itinerary reports with
custom running footers, page numbering, financial tables, and developer attribution.
"""

from datetime import datetime
import os
import re
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.pdfgen import canvas

from models.trip import Trip
from utils.calculations import format_currency
from utils.data_manager import DataManager


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that adds running footers with total page count on every page."""

    def __init__(self, *args, **kwargs):
        self.dev_info = kwargs.pop("dev_info", {})
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4B5563"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.75)
        self.line(40, 42, 572, 42)

        # Developer attribution in footer
        dev_name = self.dev_info.get("developer_name", "Developer")
        gh = self.dev_info.get("github_username", "developer")
        email = self.dev_info.get("email", "developer@smartlifeplanner.pk")
        footer_dev_text = f"Smart Life Planner | Dev: {dev_name} | GitHub: @{gh} | Email: {email}"
        self.drawString(40, 30, footer_dev_text)

        # Page numbering on right
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 30, page_str)

        self.restoreState()


class PDFReportGenerator:
    """Generates professional PDF reports for confirmed Trips and Monthly Budgets."""

    def __init__(self, data_manager: Optional[DataManager] = None):
        self.data_manager = data_manager or DataManager()
        self.reports_dir = self.data_manager.reports_dir
        self.dev_config = self.data_manager.load_developer_config()

    def _get_unique_filepath(self, prefix: str, identifier: str) -> str:
        """Generate a guaranteed unique, non-overwriting PDF filepath."""
        clean_id = re.sub(r"[^\w\-]", "_", identifier)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{clean_id}_{timestamp}.pdf"
        filepath = os.path.join(self.reports_dir, filename)

        counter = 1
        while os.path.exists(filepath):
            filename = f"{prefix}_{clean_id}_{timestamp}_{counter}.pdf"
            filepath = os.path.join(self.reports_dir, filename)
            counter += 1

        return filepath

    def generate_trip_pdf(
        self, trip: Trip, output_path: Optional[str] = None
    ) -> str:
        """Generate a professional PDF for a confirmed trip plan."""
        if not trip.confirmed:
            raise ValueError(
                "PDF reports can only be generated for confirmed trip plans. "
                "Please review and confirm the plan first."
            )

        filepath = output_path or self._get_unique_filepath("trip_report", trip.trip_id)
        self.data_manager.ensure_directory(os.path.dirname(filepath))

        dev_info = self.data_manager.load_developer_config()

        def canvas_maker(*args, **kwargs):
            return NumberedCanvas(*args, dev_info=dev_info, **kwargs)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=55,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=14,
        )
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1F2937"),
        )
        small_bold = ParagraphStyle(
            "SmallBold",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
            fontName="Helvetica-Bold",
        )

        elements = []

        # Header Title
        elements.append(Paragraph("Smart Life Planner", title_style))
        elements.append(Paragraph("Pakistan Trip Plan & Travel Itinerary Report", subtitle_style))

        # Meta Information Grid
        report_date = datetime.now().strftime("%B %d, %Y (%I:%M %p)")
        meta_data = [
            [
                Paragraph("<b>Report ID:</b>", body_style),
                Paragraph(trip.trip_id, body_style),
                Paragraph("<b>Generation Date:</b>", body_style),
                Paragraph(report_date, body_style),
            ],
            [
                Paragraph("<b>Destination:</b>", body_style),
                Paragraph(f"{trip.destination_name} ({trip.destination_type_pref})", body_style),
                Paragraph("<b>Departure City:</b>", body_style),
                Paragraph(trip.departure_city, body_style),
            ],
            [
                Paragraph("<b>Travellers:</b>", body_style),
                Paragraph(f"{trip.travellers} Person(s)", body_style),
                Paragraph("<b>Duration:</b>", body_style),
                Paragraph(f"{trip.days} Day(s), {trip.nights} Night(s)", body_style),
            ],
            [
                Paragraph("<b>Travel Category:</b>", body_style),
                Paragraph(trip.travel_category, body_style),
                Paragraph("<b>Required Rooms:</b>", body_style),
                Paragraph(f"{trip.cost_breakdown.rooms_needed if trip.cost_breakdown else 1} Room(s)", body_style),
            ],
            [
                Paragraph("<b>Transport:</b>", body_style),
                Paragraph(trip.transport_pref, body_style),
                Paragraph("<b>Accommodation:</b>", body_style),
                Paragraph(trip.accommodation_pref, body_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[90, 175, 100, 165])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # Financial Breakdown Section
        elements.append(Paragraph("Estimated Financial Breakdown", section_style))

        bd = trip.cost_breakdown
        fin_data = [
            [Paragraph("<b>Expense Component</b>", small_bold), Paragraph("<b>Calculation Basis</b>", small_bold), Paragraph("<b>Amount (PKR)</b>", small_bold)],
            [Paragraph("Transportation", body_style), Paragraph(f"{trip.travellers} traveller(s) × base cost × {trip.travel_category} tier", body_style), Paragraph(format_currency(bd.transportation), body_style)],
            [Paragraph("Accommodation", body_style), Paragraph(f"{bd.rooms_needed} room(s) × {trip.nights} night(s) (PKR 0 for 0 nights)", body_style), Paragraph(format_currency(bd.accommodation), body_style)],
            [Paragraph("Food & Meals", body_style), Paragraph(f"{trip.travellers} person(s) × {trip.days} day(s)", body_style), Paragraph(format_currency(bd.food), body_style)],
            [Paragraph("Activities & Sightseeing", body_style), Paragraph(f"Attractions, entry fees & permits for {trip.days} day(s)", body_style), Paragraph(format_currency(bd.activities), body_style)],
            [Paragraph("Emergency Allowance (5%)", body_style), Paragraph("Contingency & safety buffer on base expenses", body_style), Paragraph(format_currency(bd.emergency_allowance), body_style)],
            [Paragraph("<b>Total Estimated Trip Cost</b>", small_bold), Paragraph("Sum of all estimated categories", body_style), Paragraph(f"<b>{format_currency(bd.total_cost)}</b>", small_bold)],
            [Paragraph("<b>Estimated Cost Per Person</b>", small_bold), Paragraph(f"Total divided by {trip.travellers} traveller(s)", body_style), Paragraph(f"<b>{format_currency(bd.cost_per_person)}</b>", small_bold)],
            [Paragraph("<b>Available Budget</b>", small_bold), Paragraph("User-specified available funds", body_style), Paragraph(f"<b>{format_currency(trip.budget)}</b>", small_bold)],
        ]

        if bd.remaining_budget >= 0:
            fin_data.append([
                Paragraph("<b>Surplus Balance</b>", small_bold),
                Paragraph("Remaining unallocated budget", body_style),
                Paragraph(f"<font color='#047857'><b>{format_currency(bd.remaining_budget)}</b></font>", small_bold),
            ])
        else:
            fin_data.append([
                Paragraph("<b>Budget Shortage</b>", small_bold),
                Paragraph("Deficit amount required", body_style),
                Paragraph(f"<font color='#B91C1C'><b>{format_currency(bd.shortage)}</b></font>", small_bold),
            ])

        fin_table = Table(fin_data, colWidths=[160, 240, 130])
        fin_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#E0E7FF")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(fin_table)

        # Feasibility Box
        elements.append(Spacer(1, 8))
        status_bg = "#D1FAE5" if "within" in trip.status.lower() else "#FEE2E2"
        status_text_color = "#065F46" if "within" in trip.status.lower() else "#991B1B"
        status_p = Paragraph(
            f"<b>Feasibility Assessment:</b> <font color='{status_text_color}'><b>{trip.status.upper()}</b></font> — "
            f"{'Trip comfortably accommodates budget parameters.' if 'within' in trip.status.lower() else 'Trip requires budget optimization or parameter reduction.'}",
            body_style,
        )
        status_box = Table([[status_p]], colWidths=[530])
        status_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(status_bg)),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(status_text_color)),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(status_box)

        # Day-wise Itinerary
        if trip.itinerary:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("Day-Wise Detailed Itinerary", section_style))

            itin_rows = [
                [Paragraph("<b>Day / Title</b>", small_bold), Paragraph("<b>Scheduled Activities & Timeline</b>", small_bold), Paragraph("<b>Night Stay</b>", small_bold)]
            ]
            for item in trip.itinerary:
                sched_text = "<br/>".join([f"• {s}" for s in item.get("schedule", [])])
                itin_rows.append([
                    Paragraph(f"<b>Day {item['day']}</b><br/>{item['title']}", body_style),
                    Paragraph(sched_text, body_style),
                    Paragraph(item.get("night_stay", "N/A"), body_style),
                ])

            itin_table = Table(itin_rows, colWidths=[120, 280, 130])
            itin_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            elements.append(itin_table)

        doc.build(elements, canvasmaker=canvas_maker)
        return filepath

    def generate_budget_pdf(
        self, summary: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """Generate a professional PDF for a monthly financial budget report."""
        budget_id = summary.get("budget_id", "BUDGET")
        filepath = output_path or self._get_unique_filepath("budget_report", budget_id)
        self.data_manager.ensure_directory(os.path.dirname(filepath))

        dev_info = self.data_manager.load_developer_config()

        def canvas_maker(*args, **kwargs):
            return NumberedCanvas(*args, dev_info=dev_info, **kwargs)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=55,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#065F46"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=14,
        )
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#065F46"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1F2937"),
        )
        small_bold = ParagraphStyle(
            "SmallBold",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
            fontName="Helvetica-Bold",
        )

        elements = []

        elements.append(Paragraph("Smart Life Planner", title_style))
        elements.append(Paragraph("Monthly Financial Management & Budget Report", subtitle_style))

        # Meta table
        report_date = datetime.now().strftime("%B %d, %Y (%I:%M %p)")
        meta_data = [
            [
                Paragraph("<b>Report ID:</b>", body_style),
                Paragraph(summary["budget_id"], body_style),
                Paragraph("<b>Report Date:</b>", body_style),
                Paragraph(report_date, body_style),
            ],
            [
                Paragraph("<b>Budget Month:</b>", body_style),
                Paragraph(summary["month"], body_style),
                Paragraph("<b>Budget Type:</b>", body_style),
                Paragraph(summary["budget_type"], body_style),
            ],
            [
                Paragraph("<b>Total Available:</b>", body_style),
                Paragraph(format_currency(summary["total_available"]), body_style),
                Paragraph("<b>Total Planned:</b>", body_style),
                Paragraph(format_currency(summary["total_planned"]), body_style),
            ],
            [
                Paragraph("<b>Total Actual Spent:</b>", body_style),
                Paragraph(format_currency(summary["total_actual"]), body_style),
                Paragraph("<b>Remaining Balance:</b>", body_style),
                Paragraph(format_currency(summary["remaining_balance"]), body_style),
            ],
            [
                Paragraph("<b>Net Savings:</b>", body_style),
                Paragraph(format_currency(summary["savings"]), body_style),
                Paragraph("<b>Savings Rate:</b>", body_style),
                Paragraph(f"{summary['savings_percentage']:.1f}%", body_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[100, 165, 100, 165])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#A7F3D0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1FAE5")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # Category Breakdown Table
        elements.append(Paragraph("Category-Wise Expenditure Breakdown", section_style))

        cat_rows = [
            [
                Paragraph("<b>Category Name</b>", small_bold),
                Paragraph("<b>Planned (PKR)</b>", small_bold),
                Paragraph("<b>Actual (PKR)</b>", small_bold),
                Paragraph("<b>Variance (PKR)</b>", small_bold),
                Paragraph("<b>Status</b>", small_bold),
            ]
        ]

        for item in summary["category_breakdown"]:
            is_ov = item["status"] == "Overspent"
            status_color = "#B91C1C" if is_ov else "#047857"
            cat_rows.append([
                Paragraph(item["category"], body_style),
                Paragraph(format_currency(item["planned"]), body_style),
                Paragraph(format_currency(item["actual"]), body_style),
                Paragraph(format_currency(item["difference"]), body_style),
                Paragraph(f"<font color='{status_color}'><b>{item['status']}</b></font>", body_style),
            ])

        # Totals row
        cat_rows.append([
            Paragraph("<b>TOTALS</b>", small_bold),
            Paragraph(f"<b>{format_currency(summary['total_planned'])}</b>", small_bold),
            Paragraph(f"<b>{format_currency(summary['total_actual'])}</b>", small_bold),
            Paragraph(f"<b>{format_currency(summary['remaining_balance'])}</b>", small_bold),
            Paragraph(
                "<font color='#B91C1C'><b>OVERSPENT</b></font>" if summary["is_overall_overspent"] else "<font color='#047857'><b>ON TRACK</b></font>",
                small_bold,
            ),
        ])

        cat_table = Table(cat_rows, colWidths=[150, 95, 95, 95, 95])
        cat_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(cat_table)

        # Overspending Alert Section
        if summary["overspent_categories"]:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("Overspending Categories & Analysis", section_style))

            over_rows = [
                [Paragraph("<b>Overspent Category</b>", small_bold), Paragraph("<b>Allocated Budget</b>", small_bold), Paragraph("<b>Actual Spent</b>", small_bold), Paragraph("<b>Excess Amount (PKR)</b>", small_bold)]
            ]
            for o in summary["overspent_categories"]:
                over_rows.append([
                    Paragraph(o["category"], body_style),
                    Paragraph(format_currency(o["planned"]), body_style),
                    Paragraph(format_currency(o["actual"]), body_style),
                    Paragraph(f"<font color='#B91C1C'>+{format_currency(o['overspent_by'])}</font>", body_style),
                ])

            over_table = Table(over_rows, colWidths=[160, 120, 120, 130])
            over_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FCA5A5")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FEE2E2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            elements.append(over_table)

        # Financial Health Summary Note
        elements.append(Spacer(1, 10))
        unalloc = summary.get("unallocated_funds", 0.0)
        unalloc_msg = f"Unallocated Budget Reserve: {format_currency(unalloc)}." if unalloc >= 0 else f"Planned budget exceeds available funds by {format_currency(abs(unalloc))}."
        summary_note = (
            f"<b>Financial Health Summary:</b> Total monthly available amount is {format_currency(summary['total_available'])}. "
            f"Actual expenses recorded sum to {format_currency(summary['total_actual'])}, leaving a remaining balance of "
            f"{format_currency(summary['remaining_balance'])} ({summary['savings_percentage']:.1f}% savings rate). {unalloc_msg}"
        )
        note_p = Paragraph(summary_note, body_style)
        note_box = Table([[note_p]], colWidths=[530])
        note_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(note_box)

        doc.build(elements, canvasmaker=canvas_maker)
        return filepath
