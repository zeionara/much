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
```

2. Make sure that file `/opt/much/load.sh` has correct values for variables `PROJECT_ROOT` and `CONDA_ROOT` (it is recommended to create symbolic link `/opt/conda` which points to an actual `anaconda` location). 

3. Set up the following crontab job:

```sh
*/15 * * * * timeout 15m /bin/bash /opt/much/load.sh
```

### Listing and downloading threads from [the arhivach website][arhivach] to update [branch][branch] dataset

To update [branch][branch] dataset perform the following steps. Note that huggingface doesn't allow to store more than 1000000 files in a single repo, therefore it is very likely that you will need to distribute files with thread content across multiple repos.

For running these commands it is recommended to create a symbolic link at the root of the cloned [branch][branch] dataset to the [much module][/much] sources.

1. Identify id of the last downloaded thread (file `index.tsv` is taken from the root of the [branch][branch] dataset):

```sh
tail -n 1 index.tsv | awk '{ print $1 }'
```

2. Open [arhivach][arhivach] and manually find offset to the thread with this id. Increasing offset involves moving farther to old threads, and decreasing the thread ids which appear on the page.

3. Update `index.tsv` by listing threads from this offset to the end:

```sh
python -m much filter -t 20 -i index.tsv -s $OFFSET
```

4. Pull threads content:

```sh
python -m much grab -n 20
```

5. Update `folder` column:

```sh
python -m much update-folder-column
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
