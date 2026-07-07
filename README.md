# GymFlow (Flask version)

A gym management prototype with two connected portals:
- **Admin Portal** (`/admin`) — manage members, classes (add class included), staff, and view reports
- **Member Portal** (`/member`) — members register/sign in, book classes, and check in

Both portals share the same SQLite database (`gymflow.db`), so data actually stays in
sync — a member registering or booking a class on the member portal shows up
immediately on the admin side, and vice versa.

## 1. Install dependencies

Make sure you have Python 3 installed, then run:

```
pip install -r requirements.txt
```

## 2. Run the app

```
python app.py
```

You should see something like:

```
* Running on http://127.0.0.1:5000
```

## 3. Open it in your browser

- Admin portal: http://127.0.0.1:5000/admin
- Member portal: http://127.0.0.1:5000/member

The database file `gymflow.db` is created automatically the first time you run the
app, with a few sample classes and staff already seeded in. No members are
pre-loaded — the member portal starts empty, and registering there (or adding a
member from the admin side) is how the members table fills up.

## 4. Resetting the data

If you want to wipe everything and start fresh, just delete the database file and
restart the app:

```
rm gymflow.db
python app.py
```

## Notes for later (when you're ready to go further)

- **Deploying this**: this app works on any host that runs Python (Render, Railway,
  Hostinger with Node.js/Python support). You'll want to move off SQLite to a
  proper hosted database (like Neon Postgres) if more than one person will use
  it at once, since SQLite is a single file and doesn't handle concurrent writers
  well at scale.
- **Real payments**: the "Payment Status" field is just a manual dropdown right now.
  Wiring this to Razorpay/Stripe would replace the manual toggle with real
  transaction data.
- **Security**: `app.secret_key` in `app.py` is a placeholder — change it to a
  random value before showing this to anyone outside your own testing.
