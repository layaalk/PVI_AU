import textgrid
import os
import json


def main(
        search_dir="~/out/aligned/arpabet_by_session",
        out_filename="mfa_output_combined.json"
):
    # initialize an empty dictionary, where we'll store our results
    filtered_intervals = {}

    # iterate over all the files we want to process/filter
    for filename in find_textgrid_files(search_dir):
        # try:
        tg = textgrid.TextGrid.fromFile(filename)

        key = filename 
        filtered_intervals[key] = {"words":[], "phonemes": []}

        for tier in tg.tiers:
            tier: textgrid.IntervalTier = tier

            # Next, iterate over the intervals/alignments for the current tier
                    
            for interval in tier.intervals:
                if tier.name != "vowels" and tier.name != "phones" and tier.name != "production":
                    continue
            
                # The following line is unnecessary, but will give PyCharm a hint as to what type we're working with
                interval: textgrid.Interval = interval

                if tier.name == "production" or tier.name == "words":
                     filtered_intervals[key]["words"].append({
                         "min_time": interval.minTime,
                         "max_time": interval.maxTime,
                         "word": interval.mark.strip() })

                # add the current interval to our output dictionary
                #else:
                else:
                    if interval.mark != "":
                        filtered_intervals[key]["phonemes"].append({
                            "min_time": interval.minTime,
                            "max_time": interval.maxTime,
                            "phoneme": interval.mark.strip(),
                            "phoneme": to_ipa("phoneme")
                        })

    # This writes a (pretty human-readable) json format
    if os.makedirs(os.path.dirname(out_filename), exist_ok=True):
        with open(out_filename, "w") as f:
            json.dump(filtered_intervals, f, indent=4)

    # Now go check out the file you just created at `mfa_output_combined.json`!





def find_textgrid_files(search_directory):
    """
    Once you start working with the full data set, I expect you'll be iterating over a bunch of TextGrid files.
    I also have a copy/pastable function `search_dir()`
    I keep handy at https://gist.github.com/rcgale/935c87ce61dc1c93e0ed6801c36adefe
    & I think it's pretty slick/useful, but probably better to start with a simplified `os.walk()` approach like below.
    """
    found = []
    for basedir, directories, files in os.walk(search_directory):
        for file in files:
            if file.endswith(".TextGrid"):
                full_path = os.path.join(basedir, file)
                found.append(full_path)
                #found.append(file)
    #string parsing
    return full_path


def to_ipa(phoneme):
    """
    Converts ARPABet phonemes to IPA. Also switches some MFA-specific conventions back to our own.
    """
    if phoneme in _PHONEME_MAP_BACK:
        return _PHONEME_MAP_BACK[phoneme]
    else:
        return phoneme


_PHONEME_MAP_BACK = {
        # Undo MFA conventions:
        "ɐ": "ʌ",
        "aw": "aʊ",
        "aj": "aɪ",
        "ow": "oʊ",
        "ej": "eɪ",
        "ɔj": "ɔɪ",

        # ARPABet to IPA:
        "AA": "ɑ",
        "AE": "æ",
        "AH": "ʌ",
        "AH0": "ə",
        "AO": "ɔ",
        "AW": "aʊ",
        "AX": "ə",
        "AY": "aɪ",
        "B": "b",
        "CH": "ʧ",
        "D": "d",
        "DH": "ð",
        "DX": "ɾ",
        "EH": "ɛ",
        "ER": "ɝ",
        "EY": "e",
        "F": "f",
        "G": "ɡ",
        "HH": "h",
        "IH": "ɪ",
        "IY": "i",
        "JH": "ʤ",
        "K": "k",
        "L": "l",
        "M": "m",
        "N": "n",
        "NG": "ŋ",
        "OW": "o",
        "OY": "ɔɪ",
        "P": "p",
        "Q": "ʔ",
        "R": "ɹ",
        "S": "s",
        "SH": "ʃ",
        "T": "t",
        "TH": "θ",
        "UH": "ʊ",
        "UW": "u",
        "V": "v",
        "W": "w",
        "Y": "j",
        "Z": "z",
        "ZH": "ʒ",
}


if __name__ == '__main__':
    main()
