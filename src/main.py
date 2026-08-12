import database
import sqlite3
from linkedin_scrape import linkedin_scrape
#def load_config():

def main():
    try:
        conn = database.connect()
    except sqlite3.Error as error:
        print(f"Error: {error}")
        raise

    database.init_tables(conn)
    linkedin_scrape(conn)
    
    try:
        database.close(conn)
    except sqlite3.Error as error:
        print(f"Error: {error}")
        raise # TODO: change this to actually handle the error. Retry?

if __name__ == "__main__":
    main()