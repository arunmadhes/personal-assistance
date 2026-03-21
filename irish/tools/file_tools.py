def read_file(path):

    try:

        with open(path,"r",encoding="utf-8") as f:

            return f.read()

    except Exception as e:

        return str(e)


def write_file(path,content):

    try:

        with open(path,"w",encoding="utf-8") as f:

            f.write(content)

        return "File written successfully"

    except Exception as e:

        return str(e)