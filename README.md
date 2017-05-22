# scradaway
Scraper in Python Deavid's way

This is a fairly simple scraper that uses PostgreSQL as a download queue.
It reads config.xml, connects to the database and from there resumes the last
download queue.

Features
----------
    - Multiple sites at once.
    - Allows for including/excluding url's using regular expression. Multiple
      expressions are allowed, one per line.
    - Extracts data as JSON, using CSS selectors. You decide how to name your
      json object keys (Properties) without having to modify the underlying table 
      structure.
    - Multithreading: by default, up to 16 threads are used to download at once.
    - Cloud-ready: as Scradaway uses PostgreSQL internal
      locking as means of correct queuing, any instance of scradaway that connects
      to the same database will colaborate with the other instances.
    - Different instances of Scradaway can work with different sites and connect
      to the same database.
    - Download is always resumed from the last state.


Quickstart
-----------------

To begin doing some work, simply adapt config.xml on scradaway/ folder to your 
needs and do:

  $ seq 2 | xargs -P8 -n1 -t python3 scradaway.py

This will start two workers with up to 16 threads each one. You can launch as
many instances as cores you have, but beware each thread uses a separate 
connection to PostgreSQL, so you will have to modify postgresql.conf:

  max_connections = 2000  # by default PostgreSQL comes with 100
  
And after that you will have to restart PostgreSQL (reload isn't enough).
