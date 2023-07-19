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
        vowel_pairs: Dict[str, VowelPair] = {}
        for word_filename, intervals in combined_intervals.items():
            print(f"Processing {word_filename}")
            try:
                vowel_pair = get_vowel_pair(intervals) #get vowel pair isn't returning so what does vowel pair store
                vowel_pairs[word_filename] = vowel_pair
            except ValueError as e:
                raise ValueError(f"Problem processing {word_filename}") from e
        write_vowel_pairs(vowel_pairs, pair_filename)


@dataclasses.dataclass
class VowelInfo:
    phoneme: str
    min: float
    max: float
    duration: float
    


class VowelPair(Tuple[VowelInfo, VowelInfo]):
    def pvi(self):
        v1, v2 = self
        return 100 * ((v1.duration - v2.duration)/( 0.5*(v1.duration + v2.duration)))
        



def get_vowel_pair(intervals) -> VowelPair:
    # print(f"'{word_filename}': {combined_intervals}")
    ipa_vowels = {"i", "ʊ", "ɪ", "u", "ɛ", "ɜ", "æ", "ə", "a", "ɒ", "ʌ", "ɔ", "aɪ", "eɪ", "ɔɪ", "aʊ", "oʊ", "ɪə", "ɛə",
                  "ʊə"}
    
    found_vowels= []
    
    for interval in intervals:
        if interval['phoneme'] in ipa_vowels:  # and len(found_vowels)<2: 
            vowel_info = VowelInfo(
                phoneme= interval['phoneme'],
                min= interval['min_time'],
                max= interval['max_time'],
                duration = interval['max_time'] - interval['min_time']
            )
            
            found_vowels.append(vowel_info) 
            # session_id = os.path.basename(word_filename).replace(".TextGrid", "")
            # print(session_id, " ")
            print (vowel_info)
            print("\n")

            if len(found_vowels) == 2:
                return VowelPair(found_vowels)
            
            # f.write(session_id)
            # f.write(phoneme_array)
            # f.write(utt_dur)
            # f.write("\n")
    raise ValueError(f"Not enough vowels in intervals!")



def write_vowel_pairs(vowel_pairs: Dict[str, VowelPair], pair_filename): #is this defining a new vowel_pairs
    with open(pair_filename, "w") as f:
        csv_writer = csv.writer(f) 
        #Participant ID, Utterance ID  ,Vowel 1 ,Vowel 1 Duration, Vowel 2, Vowel 2 Duration, PVI ,Average PVI
        csv_writer.writerow(["Filename", "Vowel 1", "Vowel 1 min", "Vowel 1 max", "Vowel 1 Duration", 
                             "Vowel 2", "Vowel 2 min", "Vowel 2 max", "Vowel 2 Duration", "PVI"])
        for filename, vowel_pair in vowel_pairs.items(): 
            vowel1, vowel2 = vowel_pair
            csv_writer.writerow([
                filename,
                vowel1.phoneme, 
                vowel1.min, 
                vowel1.max,
                f"{vowel1.duration:.3f}", 
                vowel2.phoneme, 
                vowel2.min,
                vowel2.max,
                f"{vowel2.duration:.3f}",
                f"{vowel_pair.pvi():0.5f}"
                ]) 
        # iterate over data from that file
        
        # for row in vowel_pairs:
        # row.vowel1 
            # csv_writer.writerow(#depending on data structure used in get_vowel_pair function)
        # argument depends on how I store the data from the vowel_pairs, dictionary of strings possibly.    
        


if __name__ == '__main__':
    main()
