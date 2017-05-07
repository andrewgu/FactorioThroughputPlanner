#!/usr/bin/python

import csv
import sys
import math

THROUGHPUT_FILE = "outputs.csv"
COSTS_FILE = "costs.csv"

BLUE_ASSEMBLER_PRODUCTIVITY = 0.75
#YELLOW_ASSEMBLER_PRODUCTIVITY = 1.25
ELECTRIC_MINE_PRODUCTIVITY = 1.0
CHEMICAL_PLANT_PRODUCTIVITY = 1.25
ELECTRIC_FURNACE_PRODUCTIVITY = 2
CENTRIFUGE_PRODUCTIVITY = 0.75

PRODUCTIVITY_MODIFIERS = {
    "Assembler" : BLUE_ASSEMBLER_PRODUCTIVITY,
    "Chemical Plant" : CHEMICAL_PLANT_PRODUCTIVITY,
    "Furnace" : ELECTRIC_FURNACE_PRODUCTIVITY,
    "Mine" : ELECTRIC_MINE_PRODUCTIVITY,
    "Pump" : 1.0
}

# Use this to account for rounding error in floating point division
def fudged_ceil(number):
    FUDGE_FACTOR = 0.001
    if number - math.floor(number) < FUDGE_FACTOR:
        return math.floor(number)
    else:
        return math.ceil(number)

def normalize_name(name):
    return str(name).lower()

class ThroughputData:
    def __init__(self, csvRow):
        self.mechanism = csvRow['Mechanism']
        if not self.mechanism in PRODUCTIVITY_MODIFIERS:
            raise ValueError("Mechanism for fabrication is not recognized: {0}".format(self.mechanism))
    
        self.display_name = str(csvRow['Item'])
        self.normalized_name = normalize_name(self.display_name)
        self.output_count = float(csvRow['Unit Production'])
        self.duration = float(csvRow['Duration'])
        self.throughput = 1.0 / self.duration * self.output_count * PRODUCTIVITY_MODIFIERS[self.mechanism]
    
    def pretty_print(self):
        print("Display name: {0}\tMechanism: {1}\t Unit throughput: {2}".format(self.display_name, self.mechanism, self.throughput))

class CostRecord:
    def __init__(self, display_name):
        self.display_name = display_name
        self.normalized_name = normalize_name(display_name)
        self.inputs = {}
    
    def set_input(self, normalized_name, amount):
        self.inputs[normalized_name] = amount

    def pretty_print(self):
        accum = "Display name: {0}\t".format(self.display_name)
        for k in self.inputs:
            accum += "{0}:{1} ".format(k, self.inputs[k])
        print(accum)

# throughputLookup should be a Dict of normalized_name mapped to ThroughputData objects.
class CostData:
    def __init__(self, inputFile, throughputLookup):
        self.costs = {}
        self.throughputs = throughputLookup
        
        with open(inputFile, 'rb') as srcFile:
            #srcFile.seek(3)
            csvFile = csv.DictReader(srcFile, dialect='excel')
            
            for row in csvFile:
                display_name = str(row['Output'])
                normalized_name = normalize_name(display_name)
                
                if not normalized_name in self.costs:
                    self.costs[normalized_name] = CostRecord(display_name)
                
                normalized_input_name = normalize_name(row['Input'])
                self.costs[normalized_name].set_input(normalized_input_name, float(row['Cost']))
                
                if not normalized_input_name in throughputLookup:
                    raise Exception("Missing resource specified in costs file but not in outputs file: " + normalized_input_name + " required by " + normalized_name)
    
    def contains(self, key):
        return key in self.costs
    
    def get_record(self, key):
        return self.costs[key]
    
    def pretty_print(self):
        for c in self.costs:
            self.costs[c].pretty_print()

class SolutionResourceData:
    def __init__(self, display_name, instance_count, throughputLookup):
        self.display_name = display_name
        self.normalized_name = normalize_name(display_name)
        self.instance_count = instance_count
        self.throughputData = throughputLookup[self.normalized_name]
        self.total_throughput = self.throughputData.throughput * self.instance_count
        self.mechanism = self.throughputData.mechanism
    
    def append(self, resourceData):
        if not self.normalized_name == resourceData.normalized_name:
            raise ValueError("Type mismatch on appending resource counts.")
        else:
            self.instance_count += self.instance_count
            self.total_throughput = self.throughputData.throughput * self.instance_count
    
    def round_up(self):
        self.instance_count = fudged_ceil(self.instance_count)
        self.total_throughput = self.throughputData.throughput * self.instance_count
    
    def pretty_print(self):
        print("{0}:\t{1}x {2}\t = {3} units/second".format(self.display_name, self.instance_count, self.mechanism, self.total_throughput))

def load_throughputs():
    throughputLookup = {}
    
    with open(THROUGHPUT_FILE, 'rb') as f:
        #f.seek(3) # Skip the utf-8 BOM because Python doesn't play well with it.
        reader = csv.DictReader(f, dialect='excel')
        for row in reader:
            dataRow = ThroughputData(row)
            throughputLookup[dataRow.normalized_name] = dataRow
    
    return throughputLookup

def load_resource_inputs(throughputLookup):
    return CostData(COSTS_FILE, throughputLookup)
    
def recursive_compute_resources_no_ceil(norm_name, target_throughput, throughput_lookup, cost_data, resource_list):
    record = throughput_lookup[norm_name]
    
    # special math to make floating point more tolerable
    instances = target_throughput * record.duration / record.output_count / PRODUCTIVITY_MODIFIERS[record.mechanism]
    
    resource_list.append(SolutionResourceData(record.display_name, instances, throughput_lookup))
    
    # Recursion to address sub-items.
    if cost_data.contains(norm_name):
        costRecord = cost_data.get_record(norm_name)
        for input_norm_name in costRecord.inputs:
            input_target_throughput = target_throughput * costRecord.inputs[input_norm_name]
            recursive_compute_resources_no_ceil(input_norm_name, input_target_throughput, throughput_lookup, cost_data, resource_list)
    
def pooled_recursive_compute_resources(product_normalized_name, desired_throughput, throughputLookup, costData, resourceLookup):
    resourceList = []
    recursive_compute_resources_no_ceil(product_normalized_name, desired_throughput, throughputLookup, costData, resourceList)
    
    # Merge lists
    for r in resourceList:
        if r.normalized_name in resourceLookup:
            resourceLookup[r.normalized_name].append(r)
        else:
            resourceLookup[r.normalized_name] = r

def compute_pooled_resource_instance_counts(resourceLookup, throughputLookup):
    resourceList = []
    
    for r in resourceLookup:
        resourceLookup[r].round_up()
        resourceList.append(resourceLookup[r])
    
    return resourceList
    
def unpooled_recursive_compute_resources(norm_name, target_throughput, throughput_lookup, cost_data, resource_list):
    record = throughputLookup[norm_name]
    
    # special math to make floating point more tolerable
    instances = fudged_ceil(target_throughput * record.duration / record.output_count / PRODUCTIVITY_MODIFIERS[record.mechanism])
    
    resource_list.append(SolutionResourceData(record.display_name, instances, throughputLookup))
    
    # Recursion to address sub-items.
    if cost_data.contains(norm_name):
        costRecord = cost_data.get_record(norm_name)
        for input_norm_name in costRecord.inputs:
            input_target_throughput = target_throughput * costRecord.inputs[input_norm_name]
            unpooled_recursive_compute_resources(input_norm_name, input_target_throughput, throughput_lookup, cost_data, resource_list)
    
    
def compute_resource_requirements(product_normalized_name, desired_throughput, throughputLookup, costData, pool_intermediate_products = True):
    
    if pool_intermediate_products:
        resourceLookup = {}
        #raise Exception ("Pooling not yet implemented.")
        pooled_recursive_compute_resources(product_normalized_name, desired_throughput, throughputLookup, costData, resourceLookup)
        
        return compute_pooled_resource_instance_counts(resourceLookup, throughputLookup)
        
    else:
        resourceList = []
        unpooled_recursive_compute_resources(product_normalized_name, desired_throughput, throughputLookup, costData, resourceList)
        return resourceList
    
def main():
    throughputData = load_throughputs()
    costData = load_resource_inputs(throughputData)
    
    if len(sys.argv) != 3:
        raise Exception("Invalid input, need arg format of \"[product type] [units created per second]\"")
        
    product_name = str(sys.argv[1])
    product_normalized_name = normalize_name(product_name)
    desired_throughput = float(sys.argv[2])
    
    #for t in throughputData:
    #    throughputData[t].pretty_print()
    
    #costData.pretty_print()
    
    print("Desired product: " + product_name)
    print("Desired throughput: " + str(desired_throughput))
    
    results = compute_resource_requirements(product_normalized_name, desired_throughput, throughputData, costData, pool_intermediate_products = True)
    
    print("Solution amounts:")
    for row in results:
        row.pretty_print()
    
    exit()
    
                
if __name__ == "__main__":
    main()