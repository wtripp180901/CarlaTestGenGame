import numpy
import assertion
from enum import Enum
from typing import List, Tuple, Callable
import os
import csv
from coverage_variables import *
from validity_requirements import ValidityRequirement

coverage_file_path = "out/coverage.csv"

class CoverageStates(Enum):
    BUG = 0
    COVERED = 1
    UNCOVERED = 2
    INVALID = 3

class CoverageVariableSet:
    # enumerations should be of type List[(CoverageVariable,Enum)] specifying the variable key and type of enum expected
    def __init__(self,qualitative: List[Tuple[CoverageVariable,Enum]]):
        self.qualitative = qualitative
        self.macro_bin_count = 1
        for e in [v[1] for v in qualitative]:
            self.macro_bin_count *= len(e)

    def get_enum_of_variable(self,variable: CoverageVariable):
        return next(x[1] for x in self.qualitative if x[0] == variable)

    def get_coverage_entry_key(self,parameterised_enumerations: List[Tuple[CoverageVariable,Enum]]):
        entry = [None for _ in range(len(self.qualitative))]
        assert(len(parameterised_enumerations) == len(self.qualitative))
        for e in parameterised_enumerations:
            var_name_index = [v[0] for v in self.qualitative].index(e[0])
            if type(e[1]) is self.qualitative[var_name_index][1]:
                entry[var_name_index] = e[1]
            else:
                raise Exception("Incorrect type")
        return tuple(entry)


class Coverage:
    def __init__(self,assertions: List[assertion.Assertion],coverage_variable_set: CoverageVariableSet):
        self.coverage_variable_set = coverage_variable_set
        self.micro_bin_ids = [get_micro_bin_id(a) for a in assertions]
        self.micro_bin_count = len(assertions)
        self.total_size = self.micro_bin_count * self.coverage_variable_set.macro_bin_count
        self.restrict_coverage_space(assertions)

        if os.path.isfile(coverage_file_path):
            self._covered_cases = self.parse_coverage_file()
        else:
            self._covered_cases = {}
            self.write_coverage()

    def get_num_cases(self):
        violated = 0
        covered = 0
        for macro_case in self._covered_cases.values():
            violated += len([micro_case for micro_case in macro_case if micro_case == CoverageStates.BUG])
            covered += len([micro_case for micro_case in macro_case if (micro_case == CoverageStates.COVERED or micro_case == CoverageStates.BUG)])
        return self.total_size, violated, covered
    
    def restrict_coverage_space(self,assertions: List[assertion.Assertion]):
        qual_vars = [v[0] for v in self.coverage_variable_set.qualitative]
        for req in [a.validityRequirements for a in assertions]:
            if req != None:
                if req.absent_variables != None:
                    for v in req.absent_variables:
                        i = qual_vars.index(v)
                        var_width = len(self.coverage_variable_set.qualitative[i][1])
                        self.total_size -= (var_width - len(req.present_variables[v])) * (self.coverage_variable_set.macro_bin_count / var_width)
                if req.present_variables != None:
                    cum_var_width = 1
                    cum_valid_cases = 1
                    for v in req.present_variables:
                        i = qual_vars.index(v)
                        var_width = len(self.coverage_variable_set.qualitative[i][1])
                        cum_var_width *= var_width
                        cum_valid_cases *= len(req.present_variables[v])
                        if not req.all_present_required:
                            self.total_size -= len(req.present_variables[v]) * (self.coverage_variable_set.macro_bin_count / var_width)
                    if req.all_present_required:
                        self.total_size -= cum_valid_cases * (self.coverage_variable_set.macro_bin_count / cum_var_width)
        self.total_size = int(self.total_size)

    def print_coverage(self):
        total, violated, covered = self.get_num_cases()
        print(covered,"out of",total,"cases covered, ",covered/total,'% covered')
        print(violated," bugs found out of",total,"potential bugs found, ",violated/total,'%')
    
    # enumerations should be of type List[(CoverageVariable,Enum)] (should be concrete Enum e.g RainTags)
    def try_cover(self,enumerated_vars: List[Tuple[CoverageVariable,Enum]],violated_assertions: List[assertion.Assertion],covered_assertions: List[assertion.Assertion],valid_assertions: List[assertion.Assertion]):
        key = self.coverage_variable_set.get_coverage_entry_key(enumerated_vars)
        
        new_case = False
        new_uncovered = False
        
        if not (key in self._covered_cases):
            self._covered_cases[key] = [CoverageStates.INVALID for _ in range(len(self.micro_bin_ids))]
            print("New coverage bin found!")
            new_case = True
        
        for i, bin_id in enumerate(self.micro_bin_ids):
            state = self._covered_cases[key][i]
            if bin_id in [get_micro_bin_id(x) for x in valid_assertions] and state == CoverageStates.INVALID:
                self._covered_cases[key][i] = CoverageStates.UNCOVERED
                new_uncovered = True
            
            if bin_id in [get_micro_bin_id(x) for x in violated_assertions] and (state == CoverageStates.COVERED or state == CoverageStates.UNCOVERED):
                print("Undiscovered bug found for case!")
                self._covered_cases[key][i] = CoverageStates.BUG
                new_case = True
            elif bin_id in [get_micro_bin_id(x) for x in covered_assertions] and state == CoverageStates.UNCOVERED:
                print("New case found!")
                self._covered_cases[key][i] = CoverageStates.COVERED
                new_case = True
            
        if new_case:
            self.write_coverage()
            self.print_coverage()
        elif new_uncovered:
            self.write_coverage()
    
    # TODO: change so only rewrites whole file if existing row edited
    def write_coverage(self):
        fieldnames = self.get_csv_header()
        with open(coverage_file_path, 'w', newline='') as coveragefile:
            writer = csv.writer(coveragefile)
            writer.writerow(fieldnames)
            for key in self._covered_cases:
                row = [convert_criteria_value_cell(x) for x in list(key)]
                row.extend([x.name for x in list(self._covered_cases[key])])
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
                new_data = [CoverageStates[x] for x in data[i][cov_criteria_len:]]
                covered_cases[new_key] = new_data
        return covered_cases
    
    def parse_criteria_cell(self,cell: str,header_var: str):
        if cell.isdigit():
            return int(cell)
        else:
            return self.coverage_variable_set.get_enum_of_variable(CoverageVariable[header_var])[cell]

    def get_csv_header(self,include_micro_bins=True):
        fieldnames = [x[0].name for x in self.coverage_variable_set.qualitative]
        if include_micro_bins:
            fieldnames.extend(self.micro_bin_ids)
        return fieldnames
    
def get_micro_bin_id(assertion: assertion.Assertion):
    return str(assertion.ruleNumber)+"."+str(assertion.subcase)

def convert_criteria_value_cell(cell):
        if str(cell).isdigit():
            return cell
        else:
            return cell.name
        