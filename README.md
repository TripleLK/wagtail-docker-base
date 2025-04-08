This repo contains the code that will be cloned into the wagtail docker image for LLLK projects. To see the Dockerfile responsible for setting up this docker image, consult TripleLK/lllk-web-base/Dockerfile.wagtail. The code here follows this structure:

```
wagtail-docker-base
├── apps/                   # Contains the apps used by this project.
│   ├── apps/base_site/         # Contains the base_site app, which creates the base site html, 
│   │                           along with corresponding css and js, as well as the most 
│   │                           basic page model and its template.
│   ├── apps/shared/            # NOT LITERALLY CONTAINED IN REPO. As part of docker setup, 
│   │                           mount a directory here containing any apps that are to be 
│   │                           shared with the host computer or Grapes.
│   └── apps/search/            # Contains the search app, which enables search functionality
├── lllk-wagtail-base/      # The project entrypoint. Contains setup for urls, wsgi, and 
│                           general settings.
├── .gitignore              # Directs git on what files should not be committed to this repo.
├── README.md               # This file. Overview and instructions for updating internal code.
├── create_admin.py         # Python script to create basic admin user. Run by dockerfile, 
│                           creates user ``admin`` with password ``defaultpassword``. 
│                           Important that you update this password for anything going 
│                           live (instructions to come)
├── manage.py               # Management script.
└── requirements.txt        # List of Python dependencies. Pin versions as needed.
```

This repo should contain all code that is necessary for the running of wagtail in our base web setup, but that is not needed by either the host computer or the running of grapes.js. Code required by both the wagtail container and either of those should be contained within lllk-web-base.
