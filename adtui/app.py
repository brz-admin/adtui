def main():
    username = input(f"AD Username [{last_user}]: ") or last_user
    with open(LAST_USER_FILE, 'w') as f:
        f.write(username)
    app = ADTUI()
    app.run()

if __name__ == "__main__":
    main()
