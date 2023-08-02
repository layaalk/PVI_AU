import csv
import dataclasses
import json
import os
from typing import List, Tuple, Dict


#class phoneme:
    #def _init_(self, min, max, utt_dur, phoneme):
        #self.min = min
        #self.max = max
        #self.utt_dur = utt_dur
        #self.phoneme = phoneme


#list = [] 


def main(
        search_dir="/Users/layaalkhellah/PycharmProjects/AphasiaLab/",
        combined_file="mfa_output_combined.json"

):
    pair_filename = "vowel_pair_file.csv"
    min_array = []
    max_array = []
    utt_dur = []  # utterance duration
    phoneme_array = []

    with open(combined_file) as f:
        combined_intervals = json.load(f)
        vowel_pairs: List[VowelPairRow] = []
        for word_filename, intervals in combined_intervals.items():
            words = get_words(word_filename, intervals["words"], intervals["phonemes"])
            print(f"Processing {word_filename}")
            try:
                for a_word in words:
                    vowel_pair = get_vowel_pair(a_word) #get vowel pair isn't returning so what does vowel pair store
                    vowel_pairs.append(vowel_pair)
            except ValueError as e:
                raise ValueError(f"Problem processing {word_filename}") from e
        write_vowel_pairs(vowel_pairs, pair_filename)


@dataclasses.dataclass
class PhonemeInfo:
    phoneme: str
    min: float
    max: float
    duration: float

@dataclasses.dataclass
class Word:
    phonemes: List[PhonemeInfo]
    min:float
    max:float
    text: str
    filename: str



@dataclasses.dataclass
class VowelPairRow:
    first: PhonemeInfo
    second: PhonemeInfo
    word: str
    filename: str

    def pvi(self):
        return 100 * ((self.first.duration - self.second.duration)/( 0.5*(self.first.duration + self.second.duration)))
        
def get_words(filename: str, word_intervals, phoneme_intervals) -> List[Word]:
    result = []
    for word_interval in word_intervals:
        word = Word(
            phonemes = [],
            min = word_interval['min_time'],
            max = word_interval['max_time'],
            text = word_interval['word'],
            filename= filename
        )

        for interval in phoneme_intervals:
            phoneme = PhonemeInfo(
                phoneme= interval['phoneme'],
                min= interval['min_time'],
                max= interval['max_time'],
                duration = interval['max_time'] - interval['min_time']
            )
            if phoneme.min >= word.min and phoneme.max <= word.max:
                word.phonemes.append(phoneme)
        result.append(word)
    return result



def get_vowel_pair(a_word : Word) -> VowelPairRow:
    # print(f"'{word_filename}': {combined_intervals}")
    ipa_vowels = {"i", "ʊ", "ɪ", "u", "ɛ", "ɜ", "æ", "ə", "a", "ɒ", "ʌ", "ɔ", "aɪ", "eɪ", "ɔɪ", "aʊ", "oʊ", "ɪə", "ɛə",
                  "ʊə"}

    
    found_vowels= []
    
    for phoneme_info in a_word.phonemes:
        if phoneme_info.phoneme in ipa_vowels:  # and len(found_vowels)<2:      
            found_vowels.append(phoneme_info) 
            print(phoneme_info)
            print("\n")

            if len(found_vowels) == 2:
                first, second = found_vowels
                return VowelPairRow(first=first, second=second, word=a_word.text, filename=a_word.filename)
          
    raise ValueError(f"Not enough vowels in intervals!")



def write_vowel_pairs(vowel_pairs: List[VowelPairRow], pair_filename): #is this defining a new vowel_pairs
    with open(pair_filename, "w") as f:
        csv_writer = csv.writer(f) 
        #Participant ID, Utterance ID  ,Vowel 1 ,Vowel 1 Duration, Vowel 2, Vowel 2 Duration, PVI ,Average PVI
        csv_writer.writerow(["Filename", "Vowel 1", "Vowel 1 min", "Vowel 1 max", "Vowel 1 Duration", 
                             "Vowel 2", "Vowel 2 min", "Vowel 2 max", "Vowel 2 Duration", "PVI"])
        for vowel_pair in vowel_pairs: 
            csv_writer.writerow([
                vowel_pair.filename,
                vowel_pair.first.phoneme, 
                vowel_pair.first.min, 
                vowel_pair.first.max,
                f"{vowel_pair.first.duration:.3f}", 
                vowel_pair.second.phoneme, 
                vowel_pair.second.min,
                vowel_pair.second.max,
                f"{vowel_pair.second.duration:.3f}",
                f"{vowel_pair.pvi():0.5f}"
                ]) 
        # iterate over data from that file
        
        # for row in vowel_pairs:
        # row.vowel1 
            # csv_writer.writerow(#depending on data structure used in get_vowel_pair function)
        # argument depends on how I store the data from the vowel_pairs, dictionary of strings possibly.    
        


if __name__ == '__main__':
    main()
