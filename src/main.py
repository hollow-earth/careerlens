from ui import application

# TODO: Refactor scraper_utilities and move configuration to a more appropriate module.
# TODO: unload the LLM once the drain-staging part is complete

def main():
    app = application.MainApp()
    app.run()

if __name__ == "__main__":
    main()
