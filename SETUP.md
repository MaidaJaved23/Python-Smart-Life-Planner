# Smart Life Planner: frontend + web server

Copy these into your project root (next to main.py, models/, services/, pdf/, utils/, data/):

    server.py          new  (wraps your SmartLifePlanner classes and adds sign up / login)
    frontend/          new  (index.html, css/style.css, js/app.js)
    requirements.txt   adds Flask

Run:

    pip install -r requirements.txt
    python server.py          # open http://127.0.0.1:5000

Files the server uses: main.py (SmartLifePlanner), services/trip_planner.py, services/budget_manager.py,
services/feasibility_checker.py, pdf/pdf_generator.py, utils/data_manager.py, data/destinations.json.
It creates data/users.json (hashed passwords) and data/.secret. Add both to .gitignore.
Your trips.json / budgets.json / reports/ folder are used exactly as before.
