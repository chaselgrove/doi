CREATE TABLE doi (identifier TEXT NOT NULL PRIMARY KEY, 
                  metadata TEXT NOT NULL, 
                  landing_page TEXT NOT NULL);

CREATE TABLE project (doi TEXT PRIMARY KEY REFERENCES doi, 
                      xnat_id TEXT NOT NULL UNIQUE);

CREATE TABLE subject (project TEXT REFERENCES project(xnat_id), 
                      label TEXT NOT NULL, 
                      xnat_id TEXT NOT NULL UNIQUE, 
                      gender VARCHAR(6) NOT NULL 
                             CHECK (gender IN ('female', 'male')), 
                      age INTEGER NOT NULL, 
                      handedness VARCHAR(5) 
                                 CHECK (handedness IN ('left', 'right')), 
                      PRIMARY KEY (project, label));

CREATE TABLE image (doi TEXT PRIMARY KEY REFERENCES doi, 
                    project TEXT NOT NULL, 
                    subject TEXT NOT NULL, 
                    xnat_id TEXT NOT NULL UNIQUE, 
                    type VARCHAR(4) NOT NULL CHECK (type IN ('anat', 'seg')), 
                    FOREIGN KEY (project, subject) REFERENCES subject);
