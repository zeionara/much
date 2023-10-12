# much

<p align="center">
    <img src="https://i.ibb.co/zZYT9hg/logo.png"/>
    <!--<img src="assets/logo.png"/>-->
</p>

A simple utility for crawling text from 2ch

## Usage

The command `pull` requires two attributes - url of the web page to fetch and path to output file with `json` or `txt` extension depending on required output file format. For example:

```sh
python -m much pull https://2ch.hk/b/arch/2018-08-22/res/181770037.html assets/stories.txt
```

## Installation

To install through pip:

```sh
pip install much
```

To install dependencies and create conda environment:

```sh
conda env create -f environment.yml
```
