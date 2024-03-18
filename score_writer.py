import csv
import os

class ScoreWriter():
    def __init__(self,score_file_path):
         self.score_file_path = score_file_path
         self.score = 0
         if not os.path.isfile(self.score_file_path):
              self.update_score_file(0)

    def add_and_update_scenario_score(self,delta_score: int):
        if os.path.isfile(self.score_file_path):
            with open(self.score_file_path, 'r', newline='') as scorefile:
                reader = csv.reader(scorefile)
                data = list(reader)
                assert(len(data) == 2)
                self.score = int(data[1][0])
                self.score += delta_score
            self.update_score_file(self.score)
        else:
            self.update_score_file(0)

    def update_score_file(self,score: int):
        with open(self.score_file_path, 'w', newline='') as scorefile:
                writer = csv.DictWriter(scorefile, fieldnames=['score'])
                writer.writeheader()
                writer.writerow({'score': score})