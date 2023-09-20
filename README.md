# PVI_AU

TODO: Brief description/overview

## Table of Contents

- [Usage](#usage)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Step 1: `dataprep.py`](#step-1-datapreppy)
  - [Step 1: MFA alignments](#step-2-mfa-alignments)

## Usage

### Prerequisites

- Python (tested on v3.9). Recommend installing python using an environment manager. 
[Miniconda](https://docs.conda.io/projects/miniconda/en/latest/) is a good choice, since it can be used to install the other prerequisites
- [Montreal Forced Aligner (MFA)](https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html) (tested on v2.2.15)
  - Using conda: `conda install -c conda-forge montreal-forced-aligner`
- [ffmpeg](https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html) (tested on v6.0.0)
  - Using conda: `conda install -c conda-forge ffmpeg`
### Installation

Packages are managed in a requirements.txt file, which can be installed in the typical fashion:

```bash
pip install -r requirements.txt
````

### Step 1: `dataprep.py`

This step relies on an environment variable `$DATA_DIR` pointing to the source data, for example: 
```bash
DATA_DIR=./PVI_data/
```

The script `dataprep.py` does three things: it converts the manually-created `.TextGrid` files into an MFA-ready format, 
it copies/preprocesses on the corresponding audio files, and it also builds a specialized `dictionary.txt`. 
Basic usage is `python dataprep.py [options] [in_dir] [out_dir]`, with the options we explored spelled out below.

Audio pre-processing uses ffmpeg

In MFA, aligning "by session" is accomplished by preparing each transcript as a `.txt` file per audio recording.
Aligning "by word" allows MFA to take advantage of manually-annotated time alignments for each word within an audio 
recording, relying on a specially-formatted `.TextGrid` file. These files should be prepared in their own directories 
to avoid confusion when using the MFA tools.

We explored two pre-trained MFA models during the course of this work. The 
[`english_us_arpa`](https://mfa-models.readthedocs.io/en/latest/g2p/English/English%20(US)%20ARPA%20G2P%20model%20v2_0_0.html)
model expects [ARPAbet](https://en.wikipedia.org/wiki/ARPABET) transcripts, while
[`english_mfa`](https://mfa-models.readthedocs.io/en/latest/g2p/English/English%20%28US%29%20MFA%20G2P%20model%20v2_0_0.html)
expects Unicode IPA characters.

```bash
# ARPAbet transcripts, "by session":
python dataprep.py --arpabet --plain-text \
  $DATA_DIR out/prepared/arpabet_by_session

# ARPAbet transcripts, "by word":
python dataprep.py --arpabet \
  $DATA_DIR out/prepared/arpabet_by_word

# IPA transcripts, "by session":
python dataprep.py --plain-text \
  $DATA_DIR out/prepared/ipa_by_session

# IPA transcripts, "by word":
python dataprep.py \
  $DATA_DIR out/prepared/ipa_by_word
```

### Step 2: MFA alignments

```bash
############################
# Download the ARPAbet model
mfa model download acoustic english_us_arpa

# ARPAbet transcripts, "by session":
mkdir -p out/aligned/arpabet_by_session && cp -R out/prepared/arpabet_by_session/* out/aligned/arpabet_by_session
mfa align \
    out/prepared/arpabet_by_session \
    out/prepared/arpabet_by_session/dictionary.txt \
    english_us_arpa \
    out/aligned/arpabet_by_session \
    --seed=8675309 --beam=1000 --retry_beam=4000
    
# ARPAbet transcripts, "by word":
mkdir -p out/aligned/arpabet_by_word && cp -R out/prepared/arpabet_by_word/* out/aligned/arpabet_by_word
mfa align \
    out/prepared/arpabet_by_word \
    out/prepared/arpabet_by_word/dictionary.txt \
    english_us_arpa \
    out/aligned/arpabet_by_word \
    --seed=8675309 --beam=1000 --retry_beam=4000


########################
# Download the IPA model
mfa model download acoustic english_mfa

# ARPAbet transcripts, "by session":
mkdir -p out/aligned/ipa_by_session && cp -R out/prepared/ipa_by_session/* out/aligned/ipa_by_session
mfa align \
    out/prepared/ipa_by_session \
    out/prepared/ipa_by_session/dictionary.txt \
    english_us_arpa \
    out/aligned/ipa_by_session \
    --seed=8675309 --beam=1000 --retry_beam=4000
    
# ARPAbet transcripts, "by word":
mkdir -p out/aligned/ipa_by_word && cp -R out/prepared/ipa_by_word/* out/aligned/ipa_by_word
mfa align \
    out/prepared/ipa_by_word \
    out/prepared/ipa_by_word/dictionary.txt \
    english_us_arpa \
    out/aligned/ipa_by_word \
    --seed=8675309 --beam=1000 --retry_beam=4000

```

MFA can be a little bit fussy about re-running the alignments. A number of confusing problems can be
avoided by starting with a fresh working directory. There's a `--clean` option in MFA which is supposed to take care of
that, but there seem to be some quirks when using this flag in combination with other options like `--beam`. As such, 
the workspace can be manually cleaned like so:

```bash
# Be extremely careful with these ones!
rm -rf ~/Documents/MFA/arpabet_by_session
rm -rf ~/Documents/MFA/arpabet_by_word
rm -rf ~/Documents/MFA/ipa_by_session
rm -rf ~/Documents/MFA/ipa_by_word
```
