# much

<p align="center">
    <img src="https://i.ibb.co/zZYT9hg/logo.png"/>
    <!--<img src="assets/logo.png"/>-->
</p>

A simple utility for crawling text from 2ch

## Installation

To install through pip:

```sh
pip install much
```

To install dependencies and create conda environment:

```sh
conda env create -f environment.yml
```

## Usage

### Basic

The core command provided by the module is `pull`. The `pull` command lets you to download a thread from `2ch` website, and it accepts two attributes:

1. url of the web page to fetch;
2. path to output file with `json` or `txt` extension depending on required output file format.

Example:

```sh
python -m much pull https://2ch.org/b/res/328321161.html assets/test.txt
```

or

```sh
python -m much pull https://2ch.org/b/res/328321161.html assets/test.json
```

The output `txt` file is structured as follows:

1. The file consists of series of post texts, separated by single empty line.
2. Each post is put on a new line.
3. The posts are grouped into series based on how many times the post has been mentioned in posts below. The most popular posts appear at the top. Precisely, the parser works like this:
  3.1. All posts on the page are collected, recording how many times each post has been mentioned in posts below.
  3.2. The posts are sorted by decreasing number of other posts which metnion this post, increasing number of posts this post has mentioned and decreasing post text length.
  3.3. Starting from the most popular post, the series are generated recursively by adding to the series all posts which mention the original post or any post above which has already been added to the series.
  3.4. Posts which are shorter than the 15th percentile of post lengths in this thread, are not added to the output file.

Here is an example of the thread content in `txt` format:

```txt
Foo bar
Baz qux
Quux corge

Grault garply
Waldo fred
Plugh xyzzy
```

The output `json` file has a similar structure, but it is more explicit about the separation of post series. On the topmost level there is only property `topics`, which are the series mentioned above. Each series has the original post, the text of which is written to the `title` property of the items in the `topics` list, and each topic has a list of comments, located at the `comments` field. Here is an example, which corresponds to the example of `txt` file content above:

```json
{
    "topics": [
        {
            "title": "Foo bar"
            "comments": [
                "Baz qux",
                "Quux corge"
            ]
        },
        {
            "title": "Grault garply"
            "comments": [
                "Waldo fred",
                "Plugh xyzzy"
            ]
        }
    ]
}
```

It is recommended to use `txt` file as it is more compact and human-readable.

### Pulling all active threads from [the 2ch website][2ch] to update [patch][patch] dataset

The simplest call looks like:

```sh
python -m much load -r images
```

However, to run the script automatically every 15 minutes:

1. Clone the repo to the `/opt` folder:

```sh
cd /tmp
git clone git@github.com:zeionara/much.git
sudo mv much /opt
sudo chown $USERNAME:$USERNAME /opt/much
cd /opt/much
git submodule update --init
```

2. Make sure that file `/opt/much/load.sh` has correct values for variables `PROJECT_ROOT` and `CONDA_ROOT` (it is recommended to create symbolic link `/opt/conda` which points to an actual `anaconda` location):

```sh
sudo ln -s /home/zeio/miniconda3 /opt/conda
```

3. Set up the following crontab job:

```sh
*/15 * * * * timeout 15m /bin/bash /opt/much/load.sh
```

### Listing and downloading threads from [the arhivach website][arhivach] to update [branch][branch] dataset

To update [branch][branch] dataset perform the following steps. Note that huggingface doesn't allow to store more than 1000000 files in a single repo, therefore it is very likely that you will need to distribute files with thread content across multiple repos.

For running these commands it is recommended to create a symbolic link at the root of the cloned [branch][branch] dataset to the [much module](/much) sources.

1. Clone the [branch-index][branch-index] repo and [latest branch subset][branch2] repo:

```sh
cd $HOME
git clone git@hf.co:datasets/zeio/branch-index
git clone git@hf.co:datasets/zeio/branch2
```

2. Go to the repo folders and run `git lfs pull` to download large files. Then move back to the `$HOME` directory and continue from there.

3. Identify id of the last pulled thread:

```sh
tail -n 1 branch-index/index.tsv | awk '{ print $1 }'
```

4. Open [arhivach][arhivach] and manually find offset to the thread with this id. Increasing offset involves moving farther to old threads, and decreasing the thread ids which appear on the page. The last pulled post should be at the top of the page. Suppose that required offset is `715`.

5. Then to update `index.tsv` by listing threads from this offset to the end you would need python module [much][much]. It is recommended to install this module to a `$HOME` directory and create symbolic links to the module and its submodules at the cloned repo. When `much` is available from within the dataset subset folder, execute the following command from this directory:

```sh
python -m much filter -t 20 -i ../branch-index/index.tsv -s 715
```

6. Then you would need to extract entries from the global index which are relevant only to threads in the current subset:

```sh
python -m much split-index ../branch-index/index.tsv branch2
```

7. The command `filter` only pulls list of threads and saves them to `index.tsv`, but to pull the actual threads content you would need to run a separate command, this command also checks for any missing `board` ids in the `index`, and fixes them if it founds any:

```sh
python -m much grab -n 10
```

8\*. To insert missing board ids into `index.tsv`, go to the folder `branch-index`, and run `much` from there with a special flag:

```sh
python -m much grab -n 10 --update-boards
```

Then go back to the `branch2` directory, and regenerate index split:

```sh
python -m much split-index ../branch-index/index.tsv branch2
```

### Etc

The command `pull` requires two attributes - url of the web page to fetch and path to output file with `json` or `txt` extension depending on required output file format. For example:

```sh
python -m much pull https://2ch.hk/b/arch/2018-08-22/res/181770037.html assets/stories.txt
```

To fetch archived threads on `17`th page:

```sh
python -m much fetch 17
```

To list top `10` fetched threads by size (cumulative number of characters in messages longer than 100 symbols):

```sh
python -m much top 10
```

To star a thread (copy it to folder `assets/starred` with a given name):

```sh
python -m much star 263473351 discussion
```

[2ch]: https://2ch.org
[arhivach]: https://arhivach.vc
[patch]: https://huggingface.co/datasets/zeio/patch
[branch]: https://huggingface.co/datasets/zeio/branch
[branch2]: https://huggingface.co/datasets/zeio/branch2
[branch-index]: https://huggingface.co/datasets/zeio/branch-index
[much]: https://github.com/zeionara/much
