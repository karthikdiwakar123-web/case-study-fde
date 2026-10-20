# Windows Setup Guide

This guide explains how to install and run the Support Ticket Similarity Search
application on a new Windows machine. It assumes the reader is new to the project.

## 1. Windows and machine requirements

- Windows 10 or Windows 11, 64-bit. This project uses SQL Server LocalDB and
  Windows-specific setup commands; Linux and macOS are not covered.
- An internet connection for downloading installers, Python packages, npm
  packages, and the sentence-embedding model.
- Administrator access may be needed to install Windows software and SQL Server
  components.
- Allow several gigabytes of free disk space. Python's machine-learning
  dependencies and the downloaded model can use substantial space.

## 2. Software to install

Install the following software before setting up the project:

1. **Git for Windows** (if you will clone the source from GitHub):
   [git-scm.com/download/win](https://git-scm.com/download/win)
2. **Python 3.14, 64-bit**:
   [python.org/downloads/windows](https://www.python.org/downloads/windows/)
   Enable the option to add Python to PATH during installation if offered.
3. **Node.js 24 LTS** (includes npm):
   [nodejs.org/en/download](https://nodejs.org/en/download)
4. **SQL Server Express LocalDB**:
   [Microsoft SQL Server downloads](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
   and [LocalDB documentation](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/sql-server-express-localdb).
   Choose the Express edition/installer and install the LocalDB component. The
   application uses a LocalDB instance, not a separately hosted SQL Server.
5. **Microsoft ODBC Driver 17 for SQL Server**:
   [Microsoft ODBC Driver downloads](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
   The configured driver name in this project is `ODBC Driver 17 for SQL Server`.
6. **Visual Studio Code** (recommended, but not required to run the app):
   [code.visualstudio.com](https://code.visualstudio.com/)

Open a new PowerShell window after installing these tools and check that Python,
Node, and npm are available:

```powershell
py -3.14 --version
node --version
npm.cmd --version
```

The commands below use `npm.cmd` so they also work in PowerShell environments
where running the `npm.ps1` script is blocked by the execution policy. This avoids
changing the machine's PowerShell security policy.

## 3. Get the project files

If you received a ZIP file, extract it to a folder such as
`C:\Projects\case-study-fde`, then open PowerShell in that extracted folder.
The folder should contain the root `package.json` and the `backend`, `frontend`,
`data`, and `seed_scripts` directories.

Alternatively, clone the repository:

```powershell
git clone https://github.com/karthikdiwakar123-web/case-study-fde.git
Set-Location .\case-study-fde
```

For a ZIP copy, change to the folder where you extracted it instead. All commands
in the rest of this guide should be run from the project root unless a step says
otherwise.

## 4. Create the Python environment

Create a virtual environment for the backend and install its Python packages:

```powershell
py -3.14 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

The packages include FastAPI, SQLAlchemy, `pyodbc`, NumPy, and
`sentence-transformers`. Installing the machine-learning dependencies may take
some time.

## 5. Create the LocalDB instance and database

Open PowerShell and check that LocalDB is installed:

```powershell
sqllocaldb versions
```

Create and start the instance used by this application:

```powershell
sqllocaldb create TicketSimilarityDB
sqllocaldb start TicketSimilarityDB
sqllocaldb info TicketSimilarityDB
```

If the instance already exists, `create` may report that; in that case, continue
with the `start` and `info` commands.

The database itself must exist before running the seed step. Create it with
`sqlcmd`:

```powershell
sqlcmd -S "(localdb)\TicketSimilarityDB" -Q "CREATE DATABASE TicketSimilarity;"
```

If `sqlcmd` is not recognized, install Microsoft's
[SQL Server command-line utilities](https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility),
or connect to `(localdb)\TicketSimilarityDB` using the VS Code Microsoft SQL
Server extension (or another SQL client) with Windows authentication, then run:

```sql
CREATE DATABASE TicketSimilarity;
```

The application and seed script create the database tables automatically; this
step creates the database container only.

## 6. Configure the backend

Create `backend\.env` by copying the safe template:

```powershell
Copy-Item backend\.env.example backend\.env
```

The default template should work with the LocalDB instance and database created
above. Confirm that it contains:

```env
DB_DRIVER={ODBC Driver 17 for SQL Server}
DB_SERVER=(localdb)\TicketSimilarityDB
DB_NAME=TicketSimilarity
DB_TRUSTED_CONNECTION=yes

EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
```

Do not share or upload a real `.env` file if it contains private connection
details. The `.env.example` file is the safe template to distribute.

## 7. Install the Angular and root npm dependencies

The root scripts run the backend, frontend, seeding, and embedding commands. The
frontend has its own dependencies. Install both sets from the project root:

```powershell
npm.cmd ci
npm.cmd --prefix frontend ci
```

The combined `npm run dev` command expects the Angular CLI to be available as
`ng`. Install it globally:

```powershell
npm.cmd install --global @angular/cli
```

If you do not want a global Angular CLI install, you can start the frontend
separately using its project-local CLI; see [Starting the app](#9-starting-the-app).

## 8. Seed the database and generate embeddings

Run both commands from the project root, in this order:

```powershell
npm.cmd run seed
npm.cmd run embed
```

The seed command creates the `Tickets` and `TicketsNew` tables if necessary, then
loads the bundled JSON files:

- `data\tickets.json` — historical tickets and their resolution notes.
- `data\new_tickets_example.json` — incoming tickets shown in the application.

**Important:** running `npm.cmd run seed` again truncates both tables and replaces
their contents with the bundled sample data. It is not an additive import; back
up any data you need before reseeding.

The embedding command loads `all-MiniLM-L6-v2`, generates vectors for the loaded
tickets, and writes those vectors to the database. On the first run, the model
files are downloaded, so internet access is required and the command can take a
while. Similarity search will not return useful results until embeddings have
been generated.

Wait for each command to finish successfully before starting the next step. The
seed output should report ticket counts; the embedding output should confirm that
vectors were written to both tables.

## 9. Starting the app

### Start both services together

From the project root:

```powershell
npm.cmd run dev
```

Wait for both the backend and Angular development server to report that they are
ready. Open:

- **Application:** [http://localhost:4200](http://localhost:4200)
- **Backend API documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Backend health/welcome endpoint:** [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)

Keep the terminal open while using the application. Press **Ctrl+C** in that
terminal to stop the development services.

### Start services separately

Use separate PowerShell windows, with each command run from the project root.

Backend:

```powershell
npm.cmd run dev:backend
```

Frontend (uses the globally installed Angular CLI):

```powershell
npm.cmd run dev:frontend
```

If you did not install Angular CLI globally, start the frontend with its local
CLI instead:

```powershell
Set-Location .\frontend
npm.cmd start
```

Then open [http://localhost:4200](http://localhost:4200). Only one process at a
time can use each port (`8000` for the backend and `4200` for the frontend).

## 10. First-use checklist

- `sqllocaldb info TicketSimilarityDB` shows the instance is running.
- `backend\.env` exists and points to `(localdb)\TicketSimilarityDB` and
  `TicketSimilarity`.
- `npm.cmd run seed` completed and reported rows in both tables.
- `npm.cmd run embed` completed and wrote embeddings.
- The backend is responding at `http://127.0.0.1:8000/api`.
- The frontend opens at `http://localhost:4200`.

## 11. Troubleshooting

### `sqllocaldb` is not recognized

SQL Server Express LocalDB is not installed or is not available on PATH. Install
the LocalDB component and open a new terminal.

### `sqlcmd` is not recognized

The SQL command-line utilities are optional but are needed for the command shown
above. Install them, or use a SQL client with Windows authentication to create
the `TicketSimilarity` database.

### ODBC driver or database connection error

Confirm that the Microsoft ODBC Driver 17 is installed and that its installed
name matches `DB_DRIVER` in `backend\.env`. Check the instance is running with
`sqllocaldb info TicketSimilarityDB`, and make sure the database name is
`TicketSimilarity`.

### PowerShell says scripts are disabled when running npm

Use `npm.cmd` rather than `npm`; this guide uses that form to avoid changing
PowerShell's execution policy.

### Similarity search returns no matches

Confirm that `npm.cmd run embed` completed after the last seed. If the database
was reseeded, run the embedding command again before restarting the backend.

### Port 8000 or 4200 is already in use

Stop any previous backend or frontend development process using that port, then
start the app again. Do not start duplicate copies of the same service.

## Configuration and behavior notes

- The backend uses a local sentence-transformer model named
  `all-MiniLM-L6-v2`; it does not send ticket text to a hosted inference API.
- Similarity search currently uses a deliberately permissive `0.10` threshold
  for the demo scenario. Lower-confidence and false-positive matches can appear,
  so treat the results as suggestions for an agent to review.
- This setup is for local development and demonstration on Windows, not a
  production deployment.
