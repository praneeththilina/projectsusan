from app import create_app, db

app = create_app()

@app.cli.command('initdb')
def initdb_command():
    db.create_all()
    print('Initialized the database.')


if __name__ == "__main__":
    app.run()
