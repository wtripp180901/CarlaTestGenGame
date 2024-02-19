import csv
import os

score_file_path = 'out/score.csv'

def add_and_update_scenario_score(delta_score: int):
    if os.path.isfile(score_file_path):
        score = 0
        with open(score_file_path, 'r', newline='') as scorefile:
            reader = csv.reader(scorefile)
            data = list(reader)
            assert(len(data) == 2)
            score = int(data[1][0])
        update_score_file(score + delta_score)
    else:
        update_score_file(0)

def update_score_file(score: int):
    with open(score_file_path, 'w', newline='') as scorefile:
            writer = csv.DictWriter(scorefile, fieldnames=['score'])
            writer.writeheader()
            writer.writerow({'score': score})