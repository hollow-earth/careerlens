from ui import application

# TODO: replace scraper_utilities at some point, move config somewhere more natural
# TODO: unload the LLM once the drain-staging part is complete

def main():
    app = application.MainApp()
    app.run()

if __name__ == "__main__":
    main()
