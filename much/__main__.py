from click import group, argument


@group()
def main():
    pass


@main.command()
@argument('url', type = str)
def pull(url: str):
    print(f'Pulling data from {url}...')


if __name__ == '__main__':
    main()
