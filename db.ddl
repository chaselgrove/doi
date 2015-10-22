CREATE TABLE doi (identifier TEXT NOT NULL PRIMARY KEY, 
                  metadata TEXT NOT NULL, 
                  landing_page TEXT NOT NULL, 
                  up_to_date BOOLEAN NOT NULL);

CREATE TABLE project (doi TEXT PRIMARY KEY REFERENCES doi, 
                      xnat_id TEXT NOT NULL UNIQUE);

CREATE TABLE subject (project TEXT REFERENCES project(xnat_id), 
                      label TEXT NOT NULL, 
                      xnat_id TEXT NOT NULL UNIQUE, 
                      gender VARCHAR(6) NOT NULL 
                             CHECK (gender IN ('female', 'male')), 
                      age INTEGER, 
                      handedness VARCHAR(5) 
                                 CHECK (handedness IN ('left', 'right')), 
                      PRIMARY KEY (project, label));

CREATE TABLE image (doi TEXT PRIMARY KEY REFERENCES doi, 
                    project TEXT NOT NULL, 
                    subject TEXT NOT NULL, 
                    xnat_experiment_id TEXT NOT NULL, 
                    xnat_id TEXT NOT NULL UNIQUE, 
                    type VARCHAR(4) NOT NULL CHECK (type IN ('anat', 'seg')), 
                    FOREIGN KEY (project, subject) REFERENCES subject);

CREATE TABLE collection (id TEXT PRIMARY KEY, 
                         doi TEXT DEFAULT NULL REFERENCES doi);

CREATE TABLE collection_image (collection TEXT REFERENCES collection, 
                               image TEXT REFERENCES image, 
                               PRIMARY KEY (collection, image));

CREATE TABLE collection_info (id SERIAL PRIMARY KEY, 
                              collection TEXT NOT NULL REFERENCES collection, 
                              description TEXT NOT NULL, 
                              pubmed_id TEXT DEFAULT NULL, 
                              pub_doi TEXT DEFAULT NULL, 
                              funder TEXT DEFAULT NULL);

CREATE TABLE collection_info_author (id SERIAL PRIMARY KEY, 
                                     collection_info INTEGER REFERENCES collection_info NOT NULL, 
                                     author TEXT NOT NULL);

CREATE TABLE search (id TEXT PRIMARY KEY, 
                     description TEXT NOT NULL, 
                     t_created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), 
                     initial_collection TEXT NOT NULL REFERENCES collection, 
                     t_modified TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), 
                     collection TEXT NOT NULL REFERENCES collection);

CREATE VIEW entity 
         AS SELECT doi, 'project' AS type FROM project 
            UNION SELECT doi, 'image' AS type FROM image 
            UNION SELECT doi, 'collection' AS type 
                    FROM collection 
                   WHERE doi IS NOT NULL;
