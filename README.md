This repo contains the code that will be cloned into the wagtail docker image for LLLK projects. To see the Dockerfile responsible for setting up this docker image, consult TripleLK/lllk-web-base/Dockerfile.wagtail. The code here follows this structure:

```
BaseWagtailRepo/
├── plugins/                # Custom plugins, Django apps, or overrides.
├── config/                 # Project-specific configuration files or settings overrides.
├── .gitignore              # Directs git on what files should not be committed to this repo.
├── README.md               # This file. Overview and instructions for updating internal code.
├── create_admin.py         # Python script to create basic admin user. Run by dockerfile, creates user ``admin`` with password ``defaultpassword``. Important that you update this password for anything going live (instructions to come)
├── manage.py               # Management script.
└── requirements.txt        # List of Python dependencies. Pin versions as needed.
```

This repo should contain all code that is necessary for the running of wagtail in our base web setup, but that is not needed by either the host computer or the running of grapes.js. Code required by both the wagtail container and either of those should be contained within lllk-web-base.
