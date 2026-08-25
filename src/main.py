from pipeline import pipeline
from ui import application

# TODO: replace scraper_utilities at some point, move config somewhere more natural

def main():
    pipeline()

if __name__ == "__main__":
    #main()
    app = application.TableApp()
    app.run()
