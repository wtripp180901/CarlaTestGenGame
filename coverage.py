import numpy
from tags import *
import assertion
from enum import Enum
from typing import List, Dict
import os
import csv

coverage_file_path = "out/coverage.csv"

class CoverageVariable(Enum):
    RAIN = 0
    NUM_ACTORS = 1

class CoverageVariableSet:
    # enumerations should be of type List[(CoverageVariable,Enum)] specifying the variable key and type of enum expected
    # hyperparams should be of type List[(CoverageVariable,int)] specifying the variable key and max value
    def __init__(self,enumerations,hyperparams):
        self.enumerations = enumerations
        self.hyperparams = hyperparams
        self.macro_space_size = 1
        for e in [v[1] for v in enumerations]:
            self.macro_space_size *= len(e)
        for max_val in [v[1] for v in hyperparams]:
            self.macro_space_size *= max_val

    def get_coverage_entry_key(self,parameterised_enumerations,parameterised_hyperparams):
        entry = [None for _ in range(len(self.enumerations + self.hyperparams))]
        assert(len(parameterised_enumerations) == len(self.enumerations))
        assert(len(parameterised_hyperparams) == len(self.hyperparams))
        for e in parameterised_enumerations:
            var_name_index = [v[0] for v in self.enumerations].index(e[0])
            if type(e[1]) is self.enumerations[var_name_index][1]:
                entry[var_name_index] = e[1]
            else:
                raise Exception("Incorrect type")
        for h in parameterised_hyperparams:
            var_name_index = [v[0] for v in self.hyperparams].index(h[0])
            if h[1] <= self.hyperparams[var_name_index][1]:
                entry[len(self.enumerations) + var_name_index] = h[1]
            else:
                raise Exception("Exceeds max value")
        return tuple(entry)


class Coverage:
    def __init__(self,assertions: List[assertion.Assertion],coverage_variable_set: CoverageVariableSet):
        self.coverage_variable_set = coverage_variable_set
        self.micro_bin_ids = [a.ruleNumber for a in assertions]
        self.micro_bin_count = len(assertions)
        if os.path.isfile(coverage_file_path):
            self._covered_cases = self.parse_coverage_file()
        else:
            self._covered_cases = {}
            self.write_coverage()

    variable_enum_map = {
        CoverageVariable.RAIN: RainTags
    }

    def get_total_size(self):
        return self.coverage_variable_set.macro_space_size * self.micro_bin_count
    
    def get_covered_cases(self):
        covered = 0
        for macro_case in self._covered_cases.values():
            covered += len([micro_case for micro_case in macro_case if micro_case == True])
        return covered
    
    def print_coverage(self):
        covered = self.get_covered_cases()
        total = self.get_total_size()
        print(covered,"out of",total,"cases covered, ",covered/total,'% covered')
    
    # enumerations should be of type List[(CoverageVariable,Enum)] (should be concrete Enum e.g RainTags)
    # hyperparams should be of type List[(CoverageVariable,int)] (actual hyperparam not max value)
    def add_covered(self,enumerated_vars,hyperparam_vars,covered_assertion_ids: List[int]):
        key = self.coverage_variable_set.get_coverage_entry_key(enumerated_vars,hyperparam_vars)
        if not (key in self._covered_cases):
            self._covered_cases[key] = [False for _ in range(len(self.micro_bin_ids))]
        for id in covered_assertion_ids:
            self._covered_cases[key][self.micro_bin_ids.index(id)] = True
        self.write_coverage()

    
    # TODO: change so only rewrites whole file if existing row edited
    def write_coverage(self):
        fieldnames = self.get_csv_header()
        with open(coverage_file_path, 'w', newline='') as coveragefile:
            writer = csv.writer(coveragefile)
            writer.writerow(fieldnames)
            for key in self._covered_cases:
                row = [convert_criteria_value_cell(x) for x in list(key)]
                row.extend(list(self._covered_cases[key]))
                writer.writerow(row)

        
    def parse_coverage_file(self):
        covered_cases = {}
        with open(coverage_file_path, 'r', newline='') as coveragefile:
            reader = csv.reader(coveragefile)
            data = list(reader)
            headers = data[0]
            cov_criteria_len = len(self.get_csv_header(include_micro_bins=False))
            for i in range(1,len(data),1):
                new_key = data[i][:cov_criteria_len]
                for j in range(len(new_key)):
                    new_key[j] = self.parse_criteria_cell(new_key[j],headers[j])
                new_key = tuple(new_key)
                new_data = [x == "True" for x in data[i][cov_criteria_len:]]
                covered_cases[new_key] = new_data
        return covered_cases
    
    def parse_criteria_cell(self,cell: str,header_var: str):
        if cell.isdigit():
            return int(cell)
        else:
            return self.variable_enum_map[CoverageVariable[header_var]][cell]

    def get_csv_header(self,include_micro_bins=True):
        fieldnames = [x[0].name for x in self.coverage_variable_set.enumerations]
        fieldnames.extend([x[0].name for x in self.coverage_variable_set.hyperparams])
        if include_micro_bins:
            fieldnames.extend(self.micro_bin_ids)
        return fieldnames
    
def convert_criteria_value_cell(cell):
        if str(cell).isdigit():
            return cell
        else:
            return cell.name
        