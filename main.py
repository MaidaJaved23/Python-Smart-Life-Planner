#!/usr/bin/env python3
"""Smart Life Planner - Pakistan Trip Planner & Monthly Budget Manager.

Main application entry point providing terminal menu navigation,
interactive planning, financial tracking, PDF reporting, and developer info.
"""

import os
import sys
from typing import Optional, Dict, Any, List

# Add workspace directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models.trip import Trip
from models.budget import Budget
from services.trip_planner import TripPlanner
from services.budget_manager import MonthlyBudgetManager
from services.report_generator import ReportGenerator
from pdf.pdf_generator import PDFReportGenerator
from utils.data_manager import DataManager
from utils.calculations import format_currency
from utils.validators import (
    validate_positive_number,
    validate_integer,
    validate_days_and_nights,
    validate_travel_category,
    validate_destination_type,
    validate_budget_type,
    validate_date_string,
    validate_email,
)


class SmartLifePlanner:
    """Master orchestrator class for Smart Life Planner.

    Coordinates terminal menu navigation, module execution, data persistence,
    and PDF generation across Pakistan Trip Planner and Monthly Budget Manager.
    """

    def __init__(self):
        self.data_manager = DataManager()
        self.trip_planner = TripPlanner(self.data_manager)
        self.budget_manager = MonthlyBudgetManager(self.data_manager)
        self.pdf_generator = PDFReportGenerator(self.data_manager)
        self.current_active_trip: Optional[Trip] = None
        self.current_active_budget: Optional[Budget] = None

        # Set default active budget if available
        all_budgets = self.budget_manager.list_budgets()
        if all_budgets:
            self.current_active_budget = all_budgets[-1]

    def run(self) -> None:
        """Main application execution loop."""
        self.print_welcome_banner()
        while True:
            choice = self.display_main_menu()
            if choice == "1":
                self.run_trip_planner_menu()
            elif choice == "2":
                self.run_budget_manager_menu()
            elif choice == "3":
                self.run_reports_menu()
            elif choice == "4":
                self.run_developer_info_menu()
            elif choice == "5":
                self.exit_application()
                break
            else:
                print("\n[!] Invalid selection. Please enter a number between 1 and 5.")

    # =========================================================================
    # UI BANNERS & MAIN MENU
    # =========================================================================

    @staticmethod
    def print_welcome_banner() -> None:
        print("\n" + "=" * 76)
        print("          SMART LIFE PLANNER - PAKISTAN EDITION")
        print("   Integrated Pakistan Trip Planner & Monthly Budget Manager")
        print("=" * 76)
        print("Welcome! Plan intelligent journeys across Pakistan and manage household")
        print("or personal finances with automated feasibility checks and PDF reports.")
        print("=" * 76)

    @staticmethod
    def display_main_menu() -> str:
        print("\n" + "-" * 40)
        print("           MAIN APPLICATION MENU")
        print("-" * 40)
        print("  1. Pakistan Trip Planner")
        print("  2. Monthly Budget Manager")
        print("  3. View Previous Reports & Records")
        print("  4. Developer Information")
        print("  5. Exit")
        print("-" * 40)
        return input("Enter your choice (1-5): ").strip()

    @staticmethod
    def exit_application() -> None:
        print("\n" + "=" * 76)
        print("Thank you for using Smart Life Planner! Have safe travels and sound finances.")
        print("=" * 76 + "\n")

    # =========================================================================
    # MODULE ONE: PAKISTAN TRIP PLANNER MENU
    # =========================================================================

    def run_trip_planner_menu(self) -> None:
        while True:
            print("\n" + "=" * 48)
            print("       MODULE 1: PAKISTAN TRIP PLANNER")
            print("=" * 48)
            print("  1. Plan a New Trip")
            print("  2. Modify In-Progress / Active Trip")
            print("  3. View Confirmed Trip Plans")
            print("  4. Explore Pakistan Destinations Database")
            print("  5. Return to Main Menu")
            print("-" * 48)
            choice = input("Select an option (1-5): ").strip()

            if choice == "1":
                self.handle_plan_new_trip()
            elif choice == "2":
                self.handle_modify_trip()
            elif choice == "3":
                self.handle_view_confirmed_trips()
            elif choice == "4":
                self.handle_explore_destinations()
            elif choice == "5":
                break
            else:
                print("\n[!] Invalid selection. Please choose 1 through 5.")

    def handle_explore_destinations(self) -> None:
        print("\n" + "=" * 80)
        print("                   PAKISTAN DESTINATIONS DATABASE")
        print("   (Note: Costs are standard seasonal estimates, not guaranteed market rates)")
        print("=" * 80)
        for dest in self.trip_planner.destinations.values():
            print(f"\n* {dest.name.upper()} [{dest.category} | Region: {dest.region}]")
            print(f"  Description    : {dest.description}")
            print(f"  Room Capacity  : {dest.room_capacity} persons per room")
            print(f"  Base Transport : {format_currency(dest.base_transport_cost)} / person")
            print(f"  Base Hotel/Room: {format_currency(dest.base_accommodation_cost)} / night")
            print(f"  Base Food Cost : {format_currency(dest.base_food_cost)} / person / day")
            print(f"  Base Activities: {format_currency(dest.base_activities_cost)} / person / day")
            if dest.attractions:
                print(f"  Key Attractions: {', '.join(dest.attractions[:3])}...")
        print("\n" + "=" * 80)

    def handle_plan_new_trip(self) -> None:
        print("\n--- Plan a New Pakistan Trip ---")

        # 1. Available Budget
        while True:
            b_in = input("Enter available budget in PKR (e.g. 75000): ").strip()
            b_res = validate_positive_number(b_in, "Available Budget", allow_zero=False)
            if b_res.is_valid:
                budget = b_res.value
                break
            print(f"[!] {b_res.error_message}")

        # 2. Number of travellers
        while True:
            t_in = input("Enter number of travellers (e.g. 2): ").strip()
            t_res = validate_integer(t_in, "Number of travellers", min_val=1, max_val=100)
            if t_res.is_valid:
                travellers = t_res.value
                break
            print(f"[!] {t_res.error_message}")

        # 3. Destination Type Preference
        print("\nSelect Preferred Destination Type:")
        print("  1. Mountains\n  2. Historical Places\n  3. Lakes & Nature\n  4. Any")
        dtype_choice = input("Choose (1-4, default 4): ").strip()
        type_mapping = {"1": "Mountains", "2": "Historical Places", "3": "Lakes & Nature", "4": "Any"}
        dest_type = type_mapping.get(dtype_choice, "Any")

        # 4. Destination Selection
        matching_destinations = self.trip_planner.get_destinations_by_category(dest_type)
        print(f"\nAvailable Destinations matching '{dest_type}':")
        for i, d in enumerate(matching_destinations, 1):
            print(f"  {i}. {d.name} ({d.category}, {d.region})")

        while True:
            d_choice = input(f"Select destination (1-{len(matching_destinations)} or type name): ").strip()
            selected_dest = None
            if d_choice.isdigit() and 1 <= int(d_choice) <= len(matching_destinations):
                selected_dest = matching_destinations[int(d_choice) - 1]
                break
            else:
                found = self.trip_planner.get_destination(d_choice)
                if found:
                    selected_dest = found
                    break
            print("[!] Invalid destination selection. Please try again.")

        # 5. Departure City
        dep_city = input("\nEnter departure city (e.g. Islamabad, Lahore, Karachi) [Default: Islamabad]: ").strip()
        if not dep_city:
            dep_city = "Islamabad"

        # 6. Days and Nights
        while True:
            print("\nEnter trip duration (Note: Day trips can have 0 nights):")
            d_in = input("  Number of days (min 1): ").strip()
            n_in = input("  Number of nights (min 0): ").strip()
            valid_dn, days, nights, dn_err = validate_days_and_nights(d_in, n_in)
            if valid_dn:
                break
            print(f"[!] {dn_err}")

        # 7. Travel Category
        print("\nSelect Travel Category:")
        print("  1. Budget (Public Transport & Economy Guesthouses)")
        print("  2. Standard (AC Coaster / Saloon & 3-Star Hotels)")
        print("  3. Premium (Private 4x4 SUV / Flights & Luxury Resorts)")
        cat_choice = input("Choose category (1-3) [Default: 2 - Standard]: ").strip()
        cat_mapping = {"1": "Budget", "2": "Standard", "3": "Premium"}
        travel_category = cat_mapping.get(cat_choice, "Standard")

        # Create Plan
        try:
            trip, breakdown, status, status_msg = self.trip_planner.create_trip_plan(
                budget=budget,
                travellers=travellers,
                destination_name_or_id=selected_dest.id,
                departure_city=dep_city,
                days=days,
                nights=nights,
                travel_category=travel_category,
                destination_type_pref=dest_type,
            )
            self.current_active_trip = trip
        except Exception as e:
            print(f"[!] Error creating trip plan: {e}")
            return

        # Display Summary
        print("\n" + ReportGenerator.generate_trip_text_summary(trip))
        print(f"\nStatus Detail: {status_msg}")

        # Intelligent Feasibility & Optimization Check
        if "over" in status.lower():
            self.handle_trip_optimization_flow(trip)
        else:
            self.handle_trip_confirmation_flow(trip)

    def handle_trip_optimization_flow(self, trip: Trip) -> None:
        print("\n" + "!" * 76)
        print("   INTELLIGENT TRIP OPTIMIZATION: YOUR TRIP IS OVER BUDGET")
        print("!" * 76)
        dest = self.trip_planner.get_destination(trip.destination_id)
        if not dest:
            return

        # Diagnostic Explanation
        shortage_diag = self.trip_planner.get_destination(trip.destination_id)
        from services.feasibility_checker import TripFeasibilityChecker
        print(TripFeasibilityChecker.explain_shortage(trip.budget, trip.cost_breakdown))

        # Calculate Verified Alternatives
        alternatives = self.trip_planner.get_trip_alternatives(trip)
        print("\n" + ReportGenerator.generate_alternatives_comparison_table(alternatives))

        print("\nWhat would you like to do?")
        print("  1. Adopt a Recommended Feasible Alternative")
        print("  2. Manually Modify Trip Parameters (Budget, Travellers, Duration, etc.)")
        print("  3. Discard This Plan & Return to Menu")
        opt_choice = input("Enter choice (1-3): ").strip()

        if opt_choice == "1" and alternatives:
            while True:
                alt_idx = input(f"Select alternative rank to adopt (1-{len(alternatives)}) or 'c' to cancel: ").strip()
                if alt_idx.lower() == "c":
                    break
                if alt_idx.isdigit() and 1 <= int(alt_idx) <= len(alternatives):
                    chosen_opt = alternatives[int(alt_idx) - 1]
                    self.current_active_trip = chosen_opt.modified_trip
                    print(f"\n[✓] Successfully adopted alternative: '{chosen_opt.title}'!")
                    print("\n" + ReportGenerator.generate_trip_text_summary(self.current_active_trip))
                    self.handle_trip_confirmation_flow(self.current_active_trip)
                    return
                print("[!] Invalid option rank.")
        elif opt_choice == "2":
            self.handle_modify_trip()
        else:
            print("[*] Trip plan discarded. Original records remain unchanged.")

    def handle_modify_trip(self) -> None:
        if not self.current_active_trip:
            print("\n[!] No active trip in memory to modify. Please plan or load a trip first.")
            return

        base_trip = self.current_active_trip
        print("\n" + "=" * 60)
        print(f"   DYNAMIC TRIP MODIFICATION: {base_trip.trip_id}")
        print("=" * 60)
        print(f"Current Destination : {base_trip.destination_name}")
        print(f"Current Budget      : {format_currency(base_trip.budget)}")
        print(f"Current Travellers  : {base_trip.travellers}")
        print(f"Current Duration    : {base_trip.days} Day(s), {base_trip.nights} Night(s)")
        print(f"Current Category    : {base_trip.travel_category}")
        print("-" * 60)
        print("Select parameter to modify (press Enter to keep current):")

        updates: Dict[str, Any] = {}

        # 1. Budget
        b_in = input(f"New Budget (Current: {base_trip.budget}) [Enter to skip]: ").strip()
        if b_in:
            b_res = validate_positive_number(b_in, "Budget")
            if b_res.is_valid:
                updates["budget"] = b_res.value
            else:
                print(f"[!] {b_res.error_message}. Keeping current budget.")

        # 2. Travellers
        t_in = input(f"New Travellers count (Current: {base_trip.travellers}) [Enter to skip]: ").strip()
        if t_in:
            t_res = validate_integer(t_in, "Travellers", min_val=1, max_val=100)
            if t_res.is_valid:
                updates["travellers"] = t_res.value
            else:
                print(f"[!] {t_res.error_message}. Keeping current count.")

        # 3. Destination
        d_in = input(f"New Destination (Current: {base_trip.destination_name}) [Enter to skip]: ").strip()
        if d_in:
            dest_obj = self.trip_planner.get_destination(d_in)
            if dest_obj:
                updates["destination"] = dest_obj.id
            else:
                print(f"[!] Destination '{d_in}' not found. Keeping current.")

        # 4. Duration
        days_in = input(f"New Days (Current: {base_trip.days}) [Enter to skip]: ").strip()
        nights_in = input(f"New Nights (Current: {base_trip.nights}) [Enter to skip]: ").strip()
        if days_in or nights_in:
            target_days = days_in if days_in else str(base_trip.days)
            target_nights = nights_in if nights_in else str(base_trip.nights)
            v_dn, d_val, n_val, dn_err = validate_days_and_nights(target_days, target_nights)
            if v_dn:
                updates["days"] = d_val
                updates["nights"] = n_val
            else:
                print(f"[!] {dn_err}. Keeping current duration.")

        # 5. Travel Category
        cat_in = input(f"New Category (Budget/Standard/Premium) (Current: {base_trip.travel_category}) [Enter to skip]: ").strip()
        if cat_in:
            cat_res = validate_travel_category(cat_in)
            if cat_res.is_valid:
                updates["travel_category"] = cat_res.value
            else:
                print(f"[!] {cat_res.error_message}. Keeping current category.")

        if not updates:
            print("\n[*] No parameters changed. Operation cancelled.")
            return

        # Recalculate Candidate Trip Safely
        try:
            cand_trip, cand_bd, cand_status, cand_msg = self.trip_planner.modify_trip_parameters(
                base_trip, **updates
            )
        except Exception as e:
            print(f"[!] Error recalculating modified plan: {e}")
            return

        # Review Screen
        print("\n" + "=" * 70)
        print("          REVIEW MODIFIED TRIP PARAMETERS")
        print("=" * 70)
        print(f"Destination : {base_trip.destination_name} -> {cand_trip.destination_name}")
        print(f"Budget      : {format_currency(base_trip.budget)} -> {format_currency(cand_trip.budget)}")
        print(f"Travellers  : {base_trip.travellers} -> {cand_trip.travellers}")
        print(f"Duration    : {base_trip.days}D/{base_trip.nights}N -> {cand_trip.days}D/{cand_trip.nights}N")
        print(f"Category    : {base_trip.travel_category} -> {cand_trip.travel_category}")
        print(f"Total Cost  : {format_currency(base_trip.cost_breakdown.total_cost)} -> {format_currency(cand_bd.total_cost)}")
        print(f"New Status  : {cand_status} ({cand_msg})")
        print("=" * 70)

        # Confirm or Cancel
        confirm = input("\nDo you confirm these changes? (y/n): ").strip().lower()
        if confirm == "y":
            self.current_active_trip = cand_trip
            print("\n[✓] Changes confirmed! In-progress plan updated.")
            print("\n" + ReportGenerator.generate_trip_text_summary(self.current_active_trip))
            self.handle_trip_confirmation_flow(self.current_active_trip)
        else:
            print("\n[*] Modification cancelled. Previous plan preserved without changes.")

    def handle_trip_confirmation_flow(self, trip: Trip) -> None:
        print("\n" + "-" * 50)
        confirm = input("Would you like to confirm and save this trip plan? (y/n): ").strip().lower()
        if confirm == "y":
            success = self.trip_planner.confirm_and_save_trip(trip)
            if success:
                print(f"\n[✓] Trip plan {trip.trip_id} successfully confirmed and saved to database!")
                gen_pdf = input("Generate official PDF Report now? (y/n) [Default: y]: ").strip().lower()
                if gen_pdf in ["y", "yes", ""]:
                    try:
                        pdf_path = self.pdf_generator.generate_trip_pdf(trip)
                        print(f"\n[✓] Professional PDF generated successfully at:\n    {pdf_path}")
                    except Exception as e:
                        print(f"[!] Error generating PDF: {e}")
            else:
                print("[!] Failed to save trip plan.")
        else:
            print("[*] Trip plan left unconfirmed. You can continue modifying it or exit.")

    def handle_view_confirmed_trips(self) -> None:
        trips = self.trip_planner.confirmed_trips
        if not trips:
            print("\n[*] No confirmed trip plans found in database.")
            return

        print("\n" + "=" * 76)
        print("                       CONFIRMED TRIP PLANS")
        print("=" * 76)
        for i, t in enumerate(trips, 1):
            bd = t.cost_breakdown
            cost_str = format_currency(bd.total_cost) if bd else "N/A"
            print(f"  {i}. [{t.trip_id}] {t.destination_name} | {t.travellers} Pax | {t.days}D/{t.nights}N | Cost: {cost_str} | Status: {t.status}")

        print("-" * 76)
        sel = input("Select a trip number to view details / export PDF (or Enter to return): ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(trips):
            selected_trip = trips[int(sel) - 1]
            print("\n" + ReportGenerator.generate_trip_text_summary(selected_trip))
            gen_pdf = input("\nGenerate PDF Report for this trip? (y/n): ").strip().lower()
            if gen_pdf == "y":
                try:
                    pdf_path = self.pdf_generator.generate_trip_pdf(selected_trip)
                    print(f"\n[✓] PDF created at:\n    {pdf_path}")
                except Exception as e:
                    print(f"[!] Error generating PDF: {e}")

    # =========================================================================
    # MODULE TWO: MONTHLY BUDGET MANAGER MENU
    # =========================================================================

    def run_budget_manager_menu(self) -> None:
        while True:
            cur_name = self.current_active_budget.month if self.current_active_budget else "None"
            print("\n" + "=" * 54)
            print(f"   MODULE 2: MONTHLY BUDGET MANAGER (Active: {cur_name})")
            print("=" * 54)
            print("  1. Create New Monthly Budget")
            print("  2. Select / Switch Active Budget")
            print("  3. Record Actual Expense")
            print("  4. View All Expenses & Category Records")
            print("  5. Update or Delete an Expense")
            print("  6. Manage Categories (Add / Update / Remove)")
            print("  7. View Financial Summary & Overspending Analysis")
            print("  8. Generate Monthly Financial PDF Report")
            print("  9. Return to Main Menu")
            print("-" * 54)
            choice = input("Select an option (1-9): ").strip()

            if choice == "1":
                self.handle_create_budget()
            elif choice == "2":
                self.handle_select_budget()
            elif choice == "3":
                self.handle_record_expense()
            elif choice == "4":
                self.handle_view_expenses()
            elif choice == "5":
                self.handle_update_delete_expense()
            elif choice == "6":
                self.handle_manage_categories()
            elif choice == "7":
                self.handle_view_budget_summary()
            elif choice == "8":
                self.handle_generate_budget_pdf()
            elif choice == "9":
                break
            else:
                print("\n[!] Invalid selection. Please enter a number between 1 and 9.")

    def handle_create_budget(self) -> None:
        print("\n--- Create New Monthly Budget ---")

        # 1. Month
        while True:
            month = input("Enter Budget Month & Year (e.g. November 2026): ").strip()
            if month:
                break
            print("[!] Month cannot be empty.")

        # 2. Budget Type
        print("\nSelect Budget Type:")
        print("  1. Home & Kitchen (Grocery, Utilities, Rent, Kitchen, Medical, etc.)")
        print("  2. Personal Finance (Cosmetics, Gym, Shopping, Dining, Education, etc.)")
        btype_choice = input("Choose (1-2) [Default 1]: ").strip()
        budget_type = "Personal Finance" if btype_choice == "2" else "Home & Kitchen"

        # 3. Available Amount
        while True:
            amt_in = input("Enter Total Available Budget Amount in PKR (e.g. 150000): ").strip()
            amt_res = validate_positive_number(amt_in, "Available Budget Amount", allow_zero=False)
            if amt_res.is_valid:
                total_available = amt_res.value
                break
            print(f"[!] {amt_res.error_message}")

        # Create budget entity
        try:
            budget = self.budget_manager.create_budget(
                month=month,
                budget_type=budget_type,
                total_available=total_available,
            )
            self.current_active_budget = budget
            print(f"\n[✓] Budget created successfully! ID: {budget.budget_id}")
        except Exception as e:
            print(f"[!] Error creating budget: {e}")
            return

        # Prompt to set planned amounts
        set_plan = input("Would you like to allocate planned amounts to default categories now? (y/n) [Default: y]: ").strip().lower()
        if set_plan in ["y", "yes", ""]:
            print("\nEnter planned amount for each category (Press Enter to keep PKR 0.00):")
            for cat in list(budget.planned_categories.keys()):
                val = input(f"  * {cat}: ").strip()
                if val:
                    val_res = validate_positive_number(val, cat, allow_zero=True)
                    if val_res.is_valid:
                        budget.update_category(cat, val_res.value)
                    else:
                        print(f"    [!] Invalid amount. Kept at 0.00.")
            self.budget_manager.save_budgets()
            print("[✓] Category planned amounts saved.")

    def handle_select_budget(self) -> None:
        budgets = self.budget_manager.list_budgets()
        if not budgets:
            print("\n[*] No budgets found. Please create one first.")
            return

        print("\n" + "=" * 60)
        print("                AVAILABLE BUDGETS")
        print("=" * 60)
        for i, b in enumerate(budgets, 1):
            is_active = " [ACTIVE]" if (self.current_active_budget and self.current_active_budget.budget_id == b.budget_id) else ""
            print(f"  {i}. {b.month} ({b.budget_type}) - Available: {format_currency(b.total_available)}{is_active}")
        print("-" * 60)

        sel = input("Select budget number to set active: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(budgets):
            self.current_active_budget = budgets[int(sel) - 1]
            print(f"[✓] Active budget set to: {self.current_active_budget.month} ({self.current_active_budget.budget_id})")
        else:
            print("[!] Invalid selection.")

    def _require_active_budget(self) -> Optional[Budget]:
        if not self.current_active_budget:
            print("\n[!] No active budget selected. Please create or select a budget first.")
            return None
        return self.current_active_budget

    def handle_record_expense(self) -> None:
        b = self._require_active_budget()
        if not b:
            return

        print(f"\n--- Record Actual Expense for {b.month} ---")

        # Category selection
        cats = list(b.planned_categories.keys())
        print("Available Categories:")
        for i, c in enumerate(cats, 1):
            print(f"  {i}. {c}")
        print(f"  {len(cats)+1}. + Add Custom Category")

        while True:
            c_sel = input(f"Choose category (1-{len(cats)+1}) or type name: ").strip()
            chosen_cat = None
            if c_sel.isdigit():
                c_idx = int(c_sel)
                if 1 <= c_idx <= len(cats):
                    chosen_cat = cats[c_idx - 1]
                    break
                elif c_idx == len(cats) + 1:
                    custom_name = input("Enter new custom category name: ").strip()
                    if custom_name:
                        b.add_category(custom_name, 0.0)
                        chosen_cat = custom_name
                        break
            else:
                if c_sel:
                    chosen_cat = c_sel
                    break
            print("[!] Please select a valid category.")

        # Expense Amount
        while True:
            amt_in = input("Enter expense amount in PKR: ").strip()
            amt_res = validate_positive_number(amt_in, "Expense Amount", allow_zero=False)
            if amt_res.is_valid:
                amount = amt_res.value
                break
            print(f"[!] {amt_res.error_message}")

        # Description
        desc = input("Enter description / vendor (e.g. Monthly Grocery at Carrefour): ").strip()

        # Date
        while True:
            date_in = input("Enter date (YYYY-MM-DD) [Enter for today]: ").strip()
            d_res = validate_date_string(date_in)
            if d_res.is_valid:
                exp_date = d_res.value
                break
            print(f"[!] {d_res.error_message}")

        try:
            exp = self.budget_manager.record_expense(
                budget_id=b.budget_id,
                category=chosen_cat,
                description=desc,
                amount=amount,
                date=exp_date,
            )
            print(f"\n[✓] Expense recorded successfully! (ID: {exp.expense_id}, Amount: {format_currency(exp.amount)})")
        except Exception as e:
            print(f"[!] Failed to record expense: {e}")

    def handle_view_expenses(self) -> None:
        b = self._require_active_budget()
        if not b:
            return

        if not b.expenses:
            print(f"\n[*] No expenses recorded yet for {b.month}.")
            return

        print("\n" + "=" * 76)
        print(f"         EXPENSES RECORDED FOR {b.month.upper()} ({b.budget_id})")
        print("=" * 76)
        print(f"{'ID':<14} | {'Date':<11} | {'Category':<24} | {'Amount':<14} | {'Description'}")
        print("-" * 76)
        for exp in b.expenses:
            print(f"{exp.expense_id:<14} | {exp.date:<11} | {exp.category[:22]:<24} | {format_currency(exp.amount):<14} | {exp.description}")
        print("=" * 76)

    def handle_update_delete_expense(self) -> None:
        b = self._require_active_budget()
        if not b:
            return

        if not b.expenses:
            print(f"\n[*] No expenses recorded for {b.month}.")
            return

        self.handle_view_expenses()
        exp_id = input("\nEnter Expense ID to update or delete (or Enter to cancel): ").strip()
        if not exp_id:
            return

        exp = b.get_expense(exp_id)
        if not exp:
            print(f"[!] Expense ID '{exp_id}' was not found.")
            return

        print(f"\nSelected Expense: {exp.expense_id} | {exp.category} | {format_currency(exp.amount)} | {exp.description}")
        action = input("Choose action: [u]pdate or [d]elete: ").strip().lower()

        if action in ["d", "delete"]:
            confirm = input(f"Are you sure you want to delete {exp_id}? (y/n): ").strip().lower()
            if confirm == "y":
                self.budget_manager.delete_expense(b.budget_id, exp_id)
                print(f"[✓] Expense {exp_id} deleted successfully.")
        elif action in ["u", "update"]:
            print("Enter new values (press Enter to keep current):")
            new_cat = input(f"  Category [{exp.category}]: ").strip()
            new_amt_in = input(f"  Amount [{exp.amount}]: ").strip()
            new_desc = input(f"  Description [{exp.description}]: ").strip()
            new_date = input(f"  Date [{exp.date}]: ").strip()

            new_amt = None
            if new_amt_in:
                amt_res = validate_positive_number(new_amt_in, "Amount")
                if amt_res.is_valid:
                    new_amt = amt_res.value
                else:
                    print(f"[!] {amt_res.error_message}. Keeping existing.")

            try:
                self.budget_manager.update_expense(
                    budget_id=b.budget_id,
                    expense_id=exp_id,
                    category=new_cat or None,
                    description=new_desc or None,
                    amount=new_amt,
                    date=new_date or None,
                )
                print(f"[✓] Expense {exp_id} updated successfully.")
            except Exception as e:
                print(f"[!] Failed to update expense: {e}")

    def handle_manage_categories(self) -> None:
        b = self._require_active_budget()
        if not b:
            return

        print("\n" + "=" * 50)
        print(f"   MANAGE CATEGORIES FOR {b.month.upper()}")
        print("=" * 50)
        print("  1. Add New Category")
        print("  2. Update Planned Amount for a Category")
        print("  3. Remove an Existing Category")
        print("  4. Return")
        print("-" * 50)
        c_act = input("Choose option (1-4): ").strip()

        if c_act == "1":
            name = input("Enter new category name: ").strip()
            plan_in = input("Enter planned amount in PKR [Default 0.00]: ").strip()
            plan_amt = 0.0
            if plan_in:
                p_res = validate_positive_number(plan_in, "Planned Amount", allow_zero=True)
                if p_res.is_valid:
                    plan_amt = p_res.value
            try:
                self.budget_manager.add_category(b.budget_id, name, plan_amt)
                print(f"[✓] Category '{name}' added with planned amount {format_currency(plan_amt)}.")
            except Exception as e:
                print(f"[!] Error: {e}")

        elif c_act == "2":
            cats = list(b.planned_categories.keys())
            print("\nCurrent Categories:")
            for i, c in enumerate(cats, 1):
                print(f"  {i}. {c} (Current Planned: {format_currency(b.planned_categories[c])})")
            c_sel = input("Select category number to update: ").strip()
            if c_sel.isdigit() and 1 <= int(c_sel) <= len(cats):
                target_cat = cats[int(c_sel) - 1]
                amt_in = input(f"Enter new planned amount for '{target_cat}': ").strip()
                amt_res = validate_positive_number(amt_in, "Planned Amount", allow_zero=True)
                if amt_res.is_valid:
                    self.budget_manager.update_category_planned(b.budget_id, target_cat, amt_res.value)
                    print(f"[✓] Updated '{target_cat}' planned to {format_currency(amt_res.value)}.")
                else:
                    print(f"[!] {amt_res.error_message}")
            else:
                print("[!] Invalid category selection.")

        elif c_act == "3":
            cats = list(b.planned_categories.keys())
            print("\nSelect Category to Remove:")
            for i, c in enumerate(cats, 1):
                print(f"  {i}. {c}")
            c_sel = input("Enter category number to remove: ").strip()
            if c_sel.isdigit() and 1 <= int(c_sel) <= len(cats):
                target_cat = cats[int(c_sel) - 1]
                confirm = input(f"Are you sure you want to remove '{target_cat}'? (y/n): ").strip().lower()
                if confirm == "y":
                    self.budget_manager.remove_category(b.budget_id, target_cat)
                    print(f"[✓] Category '{target_cat}' removed.")
            else:
                print("[!] Invalid selection.")

    def handle_view_budget_summary(self) -> None:
        b = self._require_active_budget()
        if not b:
            return

        summary = self.budget_manager.calculate_financial_summary(b.budget_id)
        print("\n" + ReportGenerator.generate_budget_text_summary(summary))

    def handle_generate_budget_pdf(self) -> None:
        b = self._require_active_budget()
        if not b:
            return

        summary = self.budget_manager.calculate_financial_summary(b.budget_id)
        try:
            pdf_path = self.pdf_generator.generate_budget_pdf(summary)
            print(f"\n[✓] Monthly Financial Report PDF generated successfully at:\n    {pdf_path}")
        except Exception as e:
            print(f"[!] Error generating PDF: {e}")

    # =========================================================================
    # MODULE THREE: REPORTS & RECORDS VIEWER
    # =========================================================================

    def run_reports_menu(self) -> None:
        print("\n" + "=" * 60)
        print("          MODULE 3: PREVIOUS REPORTS & SAVED RECORDS")
        print("=" * 60)
        reports_dir = self.data_manager.reports_dir

        if not os.path.exists(reports_dir):
            print("[*] Reports directory is currently empty.")
            return

        pdf_files = [f for f in os.listdir(reports_dir) if f.lower().endswith(".pdf")]
        if not pdf_files:
            print("[*] No generated PDF reports found in reports/ directory.")
        else:
            print("Generated PDF Reports:")
            for i, fname in enumerate(pdf_files, 1):
                fpath = os.path.join(reports_dir, fname)
                size_kb = os.path.getsize(fpath) / 1024.0
                print(f"  {i}. {fname} ({size_kb:.1f} KB)")

        print("-" * 60)
        print(f"Confirmed Trips in Database: {len(self.trip_planner.confirmed_trips)}")
        print(f"Saved Budgets in Database  : {len(self.budget_manager.budgets)}")
        print("=" * 60)
        input("Press Enter to return to main menu...")

    # =========================================================================
    # MODULE FOUR: DEVELOPER INFORMATION MENU
    # =========================================================================

    def run_developer_info_menu(self) -> None:
        cfg = self.data_manager.load_developer_config()
        print("\n" + "=" * 60)
        print("              DEVELOPER & SYSTEM INFORMATION")
        print("=" * 60)
        print(f"Application Name  : Smart Life Planner")
        print(f"Version           : 1.0.0 (Pakistan Edition)")
        print(f"Developer Name    : {cfg.get('developer_name')}")
        print(f"GitHub Username   : @{cfg.get('github_username')}")
        print(f"Official Email    : {cfg.get('email')}")
        print(f"Python Runtime    : {sys.version.split()[0]} (Standard Library + ReportLab)")
        print("-" * 60)
        print("Core OOP Architecture:")
        print("  - Models: Destination, Trip, Expense, Budget")
        print("  - Services: TripPlanner, TripCostCalculator, TripFeasibilityChecker,")
        print("              TripOptimizer, MonthlyBudgetManager, ReportGenerator")
        print("  - PDF Engine: ReportLab SimpleDocTemplate + Custom NumberedCanvas")
        print("  - Collections: defaultdict, Counter, deque, namedtuple")
        print("=" * 60)

        edit = input("\nWould you like to update developer configuration? (y/n): ").strip().lower()
        if edit == "y":
            name = input(f"Enter Developer Name [{cfg.get('developer_name')}]: ").strip()
            gh = input(f"Enter GitHub Username [{cfg.get('github_username')}]: ").strip()
            email_in = input(f"Enter Developer Email [{cfg.get('email')}]: ").strip()

            new_cfg = {
                "developer_name": name or cfg.get("developer_name"),
                "github_username": gh or cfg.get("github_username"),
                "email": cfg.get("email"),
            }
            if email_in:
                e_res = validate_email(email_in)
                if e_res.is_valid:
                    new_cfg["email"] = e_res.value
                else:
                    print(f"[!] {e_res.error_message}. Keeping existing email.")

            self.data_manager.save_developer_config(new_cfg)
            print("[✓] Developer configuration updated successfully.")


def main() -> None:
    """Application launcher."""
    try:
        app = SmartLifePlanner()
        app.run()
    except KeyboardInterrupt:
        print("\n\n[*] Program interrupted by user. Exiting safely. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
