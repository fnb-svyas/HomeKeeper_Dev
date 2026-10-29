# Put HomeKeeper on Streamlit (about 10 minutes, no coding)

Everything in this folder is meant to be uploaded. Your private house records are not in it.

1. **Make the repository.** Sign in at github.com → **New repository** → name it `homekeeper` → choose **Public** → **Create repository**.
2. **Upload the files.** On the new repository's page, click **uploading an existing file**. Open this unzipped folder, select everything inside it (Ctrl+A), and drag it onto the page. Make sure the `.streamlit` folder is included. Wait for the list to finish, then click **Commit changes**.
3. **Deploy.** Go to share.streamlit.io → sign in with GitHub → **Create app** → **Deploy a public app from GitHub**. Repository: `<your-name>/homekeeper`; branch: `main`; main file path: `streamlit_app.py` → **Deploy**.
4. **Share.** When it finishes (a minute or two), copy the app's address from the browser and send it to Pat.

What the online version does: Browse Homes and the Ownership Score, from public records only. Each visitor's lookups and asking prices are temporary and vanish when the app restarts. The homeowner side (your own house, tasks and records) stays on your computer: `python server.py`.

To change the app later, upload the changed files to the same repository; Streamlit redeploys on its own.
