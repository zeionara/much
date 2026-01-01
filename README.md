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

Crontab entry for pulling threads every 15 minutes:

```sh
*/15 * * * * timeout 15m /bin/bash /opt/much/load.sh
```

## Usage

### Pulling all active threads from the website

```sh
python -m much load -r images
```

### Listing and downloading threads from arhivach

```sh
python -m much filter -t 20 -i index.tsv -s 17340
python -m much grab -n 20
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
