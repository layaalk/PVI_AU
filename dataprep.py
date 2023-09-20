import argparse
import csv
import json
import logging
import os
import re
import subprocess
from functools import cache
from itertools import chain
from typing import Iterator, Tuple, Set

import textgrid
from tqdm import tqdm


def get_args():
    parser = argparse.ArgumentParser(
        description="Prepares Mikala's TextGrid files for Montreal Forced Aligner."
    )
    parser.add_argument("base_dir", help="Directory to search for .TextGrid/.wav file pairs")
    parser.add_argument("out_dir", help="Where to put the prepared data")
    parser.add_argument("--tier", help="TextGrid tier that has the words", default="production")
    parser.add_argument("--arpabet", help="Whether to use ARPAbet instead of IPA", action="store_true")
    parser.add_argument("--plain-text", help="Writes files as plain text rather than TextGrid", action="store_true")
    return parser.parse_args()


def main(base_dir, out_dir, *, tier: str, arpabet: bool, plain_text: bool):
    logging.basicConfig(level=logging.INFO)

    dictionary = {}
    phones = set()
    n_written = 0

    found_files = search_dir(base_dir, r"(?:^|/)([A-Za-z0-9]+).TextGrid")
    for path, id in tqdm(list(found_files), desc="Preparing samples"):
        tg = textgrid.TextGrid.fromFile(path)
        production_tier = next(t for t in tg.tiers if t.name == tier)
        ipa_words = [interval.mark for interval in production_tier]

        for ipa_word in ipa_words:
            try:
                if arpabet:
                    dictionary[ipa_word] = ipa_to_arpa(ipa_word)
                else:
                    ipa_tokens = tokenize_ipa(ipa_word)
                    dictionary[ipa_word] = " ".join(ipa_tokens)

                phones.update(dictionary[ipa_word].split())

            except Exception as e:
                logging.info(f"ERROR! {type(e).__name__}: {e}")

        rel_dir = os.path.dirname(os.path.relpath(path, base_dir))
        sample_out_dir = os.path.join(out_dir, rel_dir)

        extension = "txt" if plain_text else "TextGrid"
        out_file = os.path.join(sample_out_dir, f"{id}.{extension}")
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

        tg.tiers.remove(tg.getFirst("vowels"))
        tg.getFirst("production").name = id.replace("chain", "")
        with open(out_file, "w") as f:
            if plain_text:
                out_transcript = " ".join(ipa_words)
                print(out_transcript, file=f)
            else:
                tg.write(f)
            n_written += 1

        wav_file = os.path.join(os.path.dirname(path), f"{id}.wav")
        if os.path.isfile(wav_file):
            out_wav_file = os.path.join(sample_out_dir, os.path.basename(wav_file))
            # shutil.copy2(wav_file, out_wav_file.replace(".wav", ".compare.wav"))
            subprocess.run([
                "ffmpeg",
                "-y",
                "-loglevel", "warning",
                "-stats",
                "-i", wav_file,
                "-filter_complex",
                "highpass=f=100,loudnorm=I=-23:LRA=7:tp=-2:print_format=json,alimiter=limit=-6dB",
                "-ac", "1",
                "-ar", "16000",
                out_wav_file
            ], check=True)
        else:
            logging.warning(f"Could not find file: {wav_file} !")

    if not arpabet:
        problem_phones = set(phones).difference(_ARPABET_TO_IPA if arpabet else _MFA_IPA)
        assert not len(problem_phones), f"These phones are going to cause problems: {problem_phones}"

    if n_written == 0:
        raise AssertionError(f"No textgrid files found in {os.path.abspath(base_dir)} !")

    logging.info(f"Prepared {n_written} samples in {out_dir}")

    if not arpabet:
        write_vowel_list(phones, os.path.join(out_dir, "vowels.json"))

    dict_path = os.path.join(out_dir, "dictionary.txt")
    with open(dict_path, "w") as dictionary_out:
        writer = csv.writer(dictionary_out, dialect=csv.excel_tab)
        for key, value in sorted(dictionary.items()):
            writer.writerow((key, value))
    logging.info(f"Wrote dictionary to {dict_path}")

    print(f"Data preparation complete. To align, run:")
    print()
    acoustic_model = 'us_english_arpa' if arpabet else 'english_mfa'
    print(f"\tmfa align {out_dir} {dict_path} {acoustic_model} [alignments_dir] [--clean]")
    print()


def write_vowel_list(phones: Set[str], filename: str):
    # If the first letter of the ARPAbet is a vowel, it's a vowel.
    vowels = sorted(p for p in phones if ipa_to_arpa(p)[0] in "AEIOU")
    with open(filename, "w") as f:
        json.dump(vowels, f)
    logging.info(f"Wrote list of vowels to {filename} . Vowels seen:")
    logging.info(f"\t{vowels}")


def search_dir(d, pattern, match_full_path=False) -> Iterator[Tuple[str, Tuple[str]]]:
    """
    Performs an `os.walk` and returns an iterator of Tuple[str, Match] for each file matching a regex pattern.
    Note that the /(groups)/ found in a regex match can be unpacked like a tuple, so enjoy!
    https://gist.github.com/rcgale/935c87ce61dc1c93e0ed6801c36adefe
    :param d: Directory to start in
    :param pattern: A str or re.Pattern to match to files
    :param match_full_path: If true, match regex against full path. If false, match regex against path relative to `d`.
    :return:
    """
    d = os.path.expanduser(d)
    if not os.path.exists(d):
        raise FileNotFoundError(f"Cannot search directory which does not exist: {d}")

    pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    for basedir, directories, files in os.walk(d):
        for file in files:
            file_path = os.path.join(basedir, file)
            if match_full_path:
                match_path = file_path
            else:
                match_path = os.path.relpath(os.path.join(basedir, file), d)
            for match in re.findall(pattern, match_path):
                yield file_path, match
                break


def ipa_to_arpa(ipa):
    arpa = []
    for ipa_token in tokenize_ipa(ipa):
        arpa_token = _IPA_TO_ARPABET.get(ipa_token, None)
        if arpa_token is None:
            raise KeyError(ipa_token)
        arpa.append(arpa_token)
    arpa_string = " ".join(arpa)
    return arpa_string


def tokenize_ipa(ipa) -> Tuple[str, ...]:
    tokens = []
    token_mapping = {**_HANDLE_SITUATIONS, **_MFA_PARTICULARS}

    for match in _ipa_token_pattern().finditer(ipa):
        ipa_token, not_ipa = match.groups()

        if ipa_token == "":
            continue

        if ipa_token in token_mapping:
            replace_sequence = token_mapping[ipa_token]
            tokens.extend(replace_sequence)
            continue

        if not_ipa:
            raise ValueError(f"Couldn't handle non-IPA symbol {not_ipa} in {ipa}")

        tokens.append(ipa_token)

    return tuple(tokens)


@cache
def _ipa_token_pattern():
    ipa_symbols = list(_IPA_TO_ARPABET)
    ipa_symbols.extend(_HANDLE_SITUATIONS)
    ipa_symbols.extend(chain(*_MFA_PARTICULARS.values()))
    ipa_symbols_long_to_short = sorted(ipa_symbols, key=lambda symbol: len(symbol.encode("utf8")), reverse=True)
    ipa_symbols_long_to_short = "|".join(re.escape(sym) for sym in ipa_symbols_long_to_short)
    pattern_str = rf"\s*({ipa_symbols_long_to_short})|(.)"
    return re.compile(pattern_str)


_ARPABET_TO_IPA = {
    "0": ("", ),
    "1": ("ˈ", ),
    "2": ("ˌ", ),
    "AA": ("ɑ", "a", "ɒ"),
    "AE": ("æ", ),
    "AH": ("ʌ",),
    "AH0": ("ə",),
    "AO": ("ɔ",),
    "AW": ("aʊ", "a͡ʊ",),
    "AX": ("ə",),
    "AY": ("aɪ", "a͡ɪ",),
    "B": ("b",),
    "CH": ("ʧ", "tʃ", "t͡ʃ",),
    "D": ("d",),
    "DH": ("ð",),
    "DX": ("ɾ",),
    "EH": ("ɛ",),
    "ER": ("ɝ", "ɜ˞", "ə˞", "ɚ",),
    "EY": ("eɪ", "e͡ɪ", "e"),
    "F": ("f",),
    "G": ("ɡ", "g",),
    "HH": ("h",),
    "IH": ("ɪ",),
    "IY": ("i",),
    "JH": ("ʤ", "dʒ", "d͡ʒ",),
    "K": ("k",),
    "L": ("l",),
    "M": ("m",),
    "N": ("n",),
    "NG": ("ŋ",),
    "OW": ("oʊ", "o͡ʊ", "o",),
    "OY": ("ɔɪ", "ɔ͡ɪ",),
    "P": ("p",),
    "Q": ("ʔ",),
    "R": ("ɹ", "r",),
    "S": ("s",),
    "SH": ("ʃ",),
    "T": ("t",),
    "TH": ("θ",),
    "UH": ("ʊ",),
    "UW": ("u",),
    "V": ("v",),
    "W": ("w",),
    "Y": ("j",),
    "Z": ("z",),
    "ZH": ("ʒ",),
}

_IPA_TO_ARPABET = {
    "": "0",
    "ˈ": "1",
    "ˌ": "2",
    "ɑ": "AA",
    "ɒ": "AA",
    "a": "AA",
    "æ": "AE",
    "ʌ": "AH",
    "ɐ": "AH",
    "ə": "AH0",
    "ɔ": "AO",
    "aʊ": "AW",
    "aw": "AW",
    "a͡ʊ": "AW",
    "aɪ": "AY",
    "aj": "AY",
    "a͡ɪ": "AY",
    "b": "B",
    "ʧ": "CH",
    "tʃ": "CH",
    "t͡ʃ": "CH",
    "d": "D",
    "ð": "DH",
    "ɾ": "D",
    "ɛ": "EH",
    "ɝ": "ER",
    "ɜ˞": "ER",
    "ə˞": "ER",
    "ɚ": "ER",
    "e": "EY",
    "eɪ": "EY",
    "ej": "EY",
    "e͡ɪ": "EY",
    "f": "F",
    "ɡ": "G",
    "g": "G",
    "h": "HH",
    "ɪ": "IH",
    "i": "IY",
    "ʤ": "JH",
    "dʒ": "JH",
    "d͡ʒ": "JH",
    "k": "K",
    "l": "L",
    "m": "M",
    "n": "N",
    "ŋ": "NG",
    "o": "OW",
    "oʊ": "OW",
    "ow": "OW",
    "o͡ʊ": "OW",
    "ɔɪ": "OY",
    "ɔj": "OY",
    "ɔ͡ɪ": "OY",
    "p": "P",
    "ʔ": "Q",
    "ɹ": "R",
    "r": "R",
    "s": "S",
    "ʃ": "SH",
    "t": "T",
    "θ": "TH",
    "ʊ": "UH",
    "u": "UW",
    "v": "V",
    "w": "W",
    "j": "Y",
    "z": "Z",
    "ʒ": "ZH",
}

_MFA_PARTICULARS = {
    # MFA uses these conventions:
    "ʌ": ["ɐ"],
    "aʊ": ["aw"],
    "aɪ": ["aj"],
    "o": ["ow"],
    "oʊ": ["ow"],
    "e": ["ej"],
    "eɪ": ["ej"],
    "ɔɪ": ["ɔj"],
}

_HANDLE_SITUATIONS = {
    ":": [""],
    "ː": [""],
    "^": [""],


    # Below are used to normalize IPA to CMUDict's phoneme inventory.
    # Many of these may not even occur.
    "ɾ": ["t"],  # DX is not in CMUDict
    "a": ["ɑ"],
    "ɑɪ": ["aɪ"],
    "ɑʊ": ["aʊ"],
    "a͡ʊ": ["aʊ"],
    "a͡ɪ": ["aɪ"],
    "tʃ": ["ʧ"],
    "t͡ʃ": ["ʧ"],
    "ɜ˞": ["ɝ"],
    "ə˞": ["ɝ"],
    "ɚ": ["ɝ"],
    "e": ["eɪ"],
    "e͡ɪ": ["eɪ"],
    "g": ["ɡ"],
    "dʒ": ["ʤ"],
    "d͡ʒ": ["ʤ"],
    # "o": ["oʊ"],
    "o͡ʊ": ["o"],
    "ɔ͡ɪ": ["ɔɪ"],
    "r": ["ɹ"],
}

_MFA_IPA = {
    'ɱ', 'ç', 'ɐ', 'ɜ', 'ʎ', 'tʷ', 'ʉː', 'θ', 'u', 'ɝ', 'ɟ', 'v', 'pʰ', 'm̩', 'dʒ', 'fʷ', 'kp', 'b', 'uː', 'ɡʷ', 'k',
    'dʲ', 'cʰ', 'ɚ', 'p', 'aː', 'ʔ', 't', 'iː', 'mʲ', 'c', 'tʃ', 'm', 'ʈʷ', 'ɑ', 'ʉ', 'ʃ', 'ow', 'e', 'ə', 'aj', 'fʲ',
    'vʲ', 'ej', 'ɛː', 'tʲ', 'əw', 'tʰ', 'ɾʲ', 'ʊ', 'l', 'æ', 'ɖ', 'j', 'ɾ̃', 's', 'z', 'eː', 'ɑː', 'ɒː', 'cʷ', 'i', 'ɾ',
    'ɒ', 'ɡ', 'ɫ', 'ɲ', 'pʲ', 'ɪ', 'ɹ', 'ɜː', 'ð', 'ɔj', 'vʷ', 'ʈ', 'ɫ̩', 'ʋ', 'd̪', 'aw', 'kʰ', 'o', 'kʷ', 'd', 't̪',
    'ɔ', 'ŋ', 'ʈʲ', 'f', 'ɡb', 'n̩', 'n', 'a', 'ʒ', 'oː', 'w', 'ɟʷ', 'h', 'bʲ', 'pʷ', 'ɛ'
}


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
