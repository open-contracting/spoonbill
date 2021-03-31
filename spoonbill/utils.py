import ijson


def iter_file(filename, root):
    with open(filename) as fd:
        reader = ijson.items(fd, f'{root}.item')
        for item in reader:
            yield item
