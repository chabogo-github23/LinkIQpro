# Neon Production Database Setup

This project now supports:

- local development with SQLite by default
- production with Neon/Postgres when `DATABASE_URL` is set

## 1. Add your Neon connection string

In `.env`, add your Neon connection string exactly as given by Neon:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require&channel_binding=require
```

Notes:

- keep `sslmode=require`
- do not commit the real connection string to git
- SQLite will still be used whenever `DATABASE_URL` is missing

## 2. Test the Neon connection

Run:

```bash
python manage.py showmigrations
```

If Django connects successfully, the command will list migrations instead of failing with a database error.

## 3. Create the Postgres schema in Neon

Run:

```bash
python manage.py migrate
```

This creates all tables in the empty Neon database using your existing Django migrations.

## 4. Export data from your current SQLite database

Before switching environments permanently, export your current SQLite data:

```bash
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --natural-foreign --natural-primary -o data.json
```

If you want to be extra safe, keep a backup copy of `db.sqlite3` too.

## 5. Load the data into Neon

After `DATABASE_URL` points to Neon and `migrate` has completed:

```bash
python manage.py loaddata data.json
```

## 6. Reset Postgres ID sequences

After importing data, run:

```bash
python manage.py sqlsequencereset apps.users apps.projects apps.payments apps.messaging apps.audit apps.negotiations core | python manage.py dbshell
```

This makes sure future inserts continue from the correct ID values.

## 7. Move uploaded files

Database migration does not move uploaded files. Your project also depends on files under `media/`, so copy that folder to your production server or object storage.

## 8. Final verification

Run these checks against Neon:

```bash
python manage.py check
python manage.py showmigrations
python manage.py createsuperuser
```

Then start the app and verify:

- login works
- projects and payments load correctly
- file links still resolve
- admin pages open correctly

## Recommended rollout

1. Keep SQLite as your local fallback.
2. Use Neon in staging/production via `.env`.
3. Export data once from SQLite.
4. Import into Neon.
5. Point production to Neon.
