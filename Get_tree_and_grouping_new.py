#!/usr/bin/python
import os
import re
import glob
import shutil
import warnings
import argparse
import itertools
import numpy as np
from ete3 import Tree
from time import sleep
from datetime import datetime
from string import ascii_uppercase
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import generic_dna
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram


def export_dna_record(gene_seq, gene_id, gene_description, output_handle):
    seq_object = Seq(gene_seq, IUPAC.unambiguous_dna)
    seq_record = SeqRecord(seq_object)
    seq_record.id = gene_id
    seq_record.description = gene_description
    SeqIO.write(seq_record, output_handle, 'fasta')


def export_aa_record(gene_seq, gene_id, gene_description, output_handle):
    seq_object = Seq(gene_seq, IUPAC.protein)
    seq_record = SeqRecord(seq_object)
    seq_record.id = gene_id
    seq_record.description = gene_description
    SeqIO.write(seq_record, output_handle, 'fasta')


def get_ffn_faa_from_gbk(prefix, input_gbk_folder, op_folder):
    # create ffn and faa folder
    faa_folder = '%s_faa_files' % prefix
    ffn_folder = '%s_ffn_files' % prefix
    pwd_faa_folder = '%s/%s' % (op_folder, faa_folder)
    pwd_ffn_folder = '%s/%s' % (op_folder, ffn_folder)
    os.mkdir(pwd_faa_folder)
    os.mkdir(pwd_ffn_folder)

    # get input gbk file list
    input_gbk_re = '%s/*.gbk' % input_gbk_folder
    input_gbk_file_list = [os.path.basename(file_name) for file_name in glob.glob(input_gbk_re)]

    # get ffn and faa file from input gbk file
    for gbk_file in input_gbk_file_list:

        # prepare file name
        gbk_file_basename, gbk_file_extension = os.path.splitext(gbk_file)
        pwd_gbk_file = '%s/%s' % (input_gbk_folder, gbk_file)
        pwd_output_ffn_file = '%s/%s.ffn' % (pwd_ffn_folder, gbk_file_basename)
        pwd_output_faa_file = '%s/%s.faa' % (pwd_faa_folder, gbk_file_basename)

        output_ffn_handle = open(pwd_output_ffn_file, 'w')
        output_faa_handle = open(pwd_output_faa_file, 'w')
        for seq_record in SeqIO.parse(pwd_gbk_file, 'genbank'):
            for feature in seq_record.features:
                if feature.type == "CDS":
                    seq_record_sequence = str(seq_record.seq)

                    # get DNA sequence
                    seq_nc = ''
                    if feature.location.strand == 1:
                        seq_nc = seq_record_sequence[feature.location.start:feature.location.end]
                    if feature.location.strand == -1:
                        nc_seq_rc = seq_record_sequence[feature.location.start:feature.location.end]
                        seq_nc = str(Seq(nc_seq_rc, generic_dna).reverse_complement())

                    # get aa sequence
                    seq_aa = feature.qualifiers['translation'][0]
                    feature_id = feature.qualifiers['locus_tag'][0]
                    feature_description = feature.qualifiers['product'][0]

                    # export to file
                    export_dna_record(seq_nc, feature_id, feature_description, output_ffn_handle)
                    export_aa_record(seq_aa, feature_id, feature_description, output_faa_handle)

        output_ffn_handle.close()
        output_faa_handle.close()


def get_rank_assignment_dict(rank, taxon_assignment_lineage_file):

    rank_to_position_dict = {'d': 1, 'p': 2, 'c': 3, 'o': 4, 'f': 5, 'g': 6, 's': 7}
    rank_position = rank_to_position_dict[rank]

    assignment_dict = {}
    for each in open(taxon_assignment_lineage_file):
        each_split = each.strip().split('\t')
        bin_name = each_split[0]
        assignment = each_split[1].split(';')
        assignment_no_num = []
        for each_assign in assignment:
            assignment_no_num.append(each_assign.split('(')[0])

        new_assign = ''
        if len(assignment_no_num) <= rank_position:
            new_assign = assignment_no_num[-1]
        elif len(assignment_no_num) > rank_position:
            new_assign = assignment_no_num[rank_position-1]

        assignment_dict[bin_name] = new_assign

    return assignment_dict


def get_group_index_list():
    def iter_all_strings():
        size = 1
        while True:
            for s in itertools.product(ascii_uppercase, repeat=size):
                yield "".join(s)
            size += 1

    group_index_list = []
    for s in iter_all_strings():
        group_index_list.append(s)
        if s == 'ZZ':
            break
    return group_index_list


def get_node_distance(tree, node_1, node_2):
    distance = tree.get_distance(node_1, node_2)
    return distance


def get_group(n):
    leaf_name = leaf_node_list[n]
    grouping_id = bin_to_grouping_dict[leaf_name]
    return '(%s)_(%s)' % (grouping_id, leaf_name)


def get_taxon(n):
    leaf_name = leaf_node_list[n]
    taxon_assign = bin_to_taxon_dict[leaf_name]
    grouping_id = bin_to_grouping_dict[leaf_name]
    return '(%s)_(%s)_(%s)' % (grouping_id, leaf_name, taxon_assign)
    #return taxon_assign


def get_distance_matrix(tree_file):

    # read in tree
    tree_in = Tree(tree_file, format=3)

    # get leaf node list
    leaf_node_list = []
    for leaf_node in tree_in:
        leaf_node_list.append(leaf_node.name)
    leaf_node_list = sorted(leaf_node_list)

    # get list of distance list
    all_distances_lol = []
    for each_node_1 in leaf_node_list:
        current_node_distance_list = []
        for each_node_2 in leaf_node_list:
            distance = 0
            if each_node_1 != each_node_2:
                distance = get_node_distance(tree_in, each_node_1, each_node_2)
                distance = float("{0:.5f}".format(distance))
            current_node_distance_list.append(str(distance))
        all_distances_lol.append(current_node_distance_list)

    return all_distances_lol


def plot_clustering_dendrogram(cluster, leaf_font_size, leaf_label_func, color_threshold, pwd_png_file):

    plt.figure(figsize=(9, 15))
    plt.xlabel('Distance')
    dendrogram(cluster, orientation='left', leaf_rotation=0, leaf_font_size=leaf_font_size, leaf_label_func=leaf_label_func, color_threshold=color_threshold)
    plt.axvline(x=max_d, c='k', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(pwd_png_file, dpi=300)
    plt.close()


os.chdir('/Users/songweizhi/Desktop/wd_new')
input_gbk_folder = 'input_gbk_files'
output_prefix = 'NorthSea'
MetaCHIP_wd = '%s_MetaCHIP_wd' % output_prefix


pwd_hmmsearch_exe = '~/Softwares/hmmer/hmmer-3.1b2-macosx-intel/binaries/hmmsearch'
path_to_hmm = '~/PycharmProjects/MetaCHIP/phylo.hmm'
pwd_mafft_exe = 'mafft'
pwd_fasttree_exe = '~/Softwares/FastTree/FastTree'
taxon_classification_file = None
selected_rank = 'c'
max_d = None
leaf_font_size = 6
add_group_to_tree_R = '~/R_scripts/newick_tree/add_group_to_tree.R'


# disable warnings
warnings.filterwarnings("ignore")


# create MetaCHIP outputs folder
if os.path.isdir(MetaCHIP_wd):
    shutil.rmtree(MetaCHIP_wd, ignore_errors=True)
    if os.path.isdir(MetaCHIP_wd):
        shutil.rmtree(MetaCHIP_wd, ignore_errors=True)
        if os.path.isdir(MetaCHIP_wd):
            shutil.rmtree(MetaCHIP_wd, ignore_errors=True)
    os.makedirs(MetaCHIP_wd)
else:
    os.makedirs(MetaCHIP_wd)

########################################## get ffn and faa file from gbk files #########################################

get_ffn_faa_from_gbk(output_prefix, input_gbk_folder, MetaCHIP_wd)


################################################### get species tree ###################################################

# define file name
SCG_tree_wd =                   '%s_get_SCG_tree_wd'        % output_prefix
combined_alignment_file =       '%s_species_tree.aln'       % output_prefix
newick_tree_file =              '%s_species_tree.newick'    % output_prefix
pwd_SCG_tree_wd =               '%s/%s'                     % (MetaCHIP_wd, SCG_tree_wd)
pwd_combined_alignment_file =   '%s/%s'                     % (MetaCHIP_wd, combined_alignment_file)
pwd_newick_tree_file =          '%s/%s'                     % (MetaCHIP_wd, newick_tree_file)
os.mkdir(pwd_SCG_tree_wd)


faa_file_re = '%s/%s_faa_files/*.faa' % (MetaCHIP_wd, output_prefix)
faa_file_list = [os.path.basename(file_name) for file_name in glob.glob(faa_file_re)]
faa_file_list = sorted(faa_file_list)

faa_file_basename_list = []
for faa_file in faa_file_list:
    faa_file_basename, faa_file_extension = os.path.splitext(faa_file)
    faa_file_basename_list.append(faa_file_basename)


for faa_file_basename in faa_file_basename_list:

    # run hmmsearch
    pwd_faa_file = '%s/%s_faa_files/%s.faa' % (MetaCHIP_wd, output_prefix, faa_file_basename)
    os.system('%s -o /dev/null --domtblout %s/%s_hmmout.tbl %s %s' % (pwd_hmmsearch_exe, pwd_SCG_tree_wd, faa_file_basename, path_to_hmm, pwd_faa_file))

    # Reading the protein file in a dictionary
    proteinSequence = {}
    for seq_record in SeqIO.parse(pwd_faa_file, 'fasta'):
        proteinSequence[seq_record.id] = str(seq_record.seq)

    # Reading the hmmersearch table/extracting the protein part found beu hmmsearch out of the protein/Writing each protein sequence that was extracted to a fasta file (one for each hmm in phylo.hmm
    hmm_id = ''
    hmm_name = ''
    hmm_pos1 = 0
    hmm_pos2 = 0
    hmm_score = 0

    with open(pwd_SCG_tree_wd + '/' + faa_file_basename + '_hmmout.tbl', 'r') as tbl:
        for line in tbl:
            if line[0] == "#": continue
            line = re.sub('\s+', ' ', line)
            splitLine = line.split(' ')

            if (hmm_id == ''):
                hmm_id = splitLine[4]
                hmm_name = splitLine[0]
                hmm_pos1 = int(splitLine[17]) - 1
                hmm_pos2 = int(splitLine[18])
                hmm_score = float(splitLine[13])
            elif (hmm_id == splitLine[4]):
                if (float(splitLine[13]) > hmm_score):
                    hmm_name = splitLine[0]
                    hmm_pos1 = int(splitLine[17]) - 1
                    hmm_pos2 = int(splitLine[18])
                    hmm_score = float(splitLine[13])
            else:
                file_out = open(pwd_SCG_tree_wd + '/' + hmm_id + '.fasta', 'a+')
                file_out.write('>' + faa_file_basename + '\n')
                if hmm_name != '':
                    seq = str(proteinSequence[hmm_name][hmm_pos1:hmm_pos2])
                file_out.write(str(seq) + '\n')
                file_out.close()
                hmm_id = splitLine[4]
                hmm_name = splitLine[0]
                hmm_pos1 = int(splitLine[17]) - 1
                hmm_pos2 = int(splitLine[18])
                hmm_score = float(splitLine[13])

        else:
            file_out = open(pwd_SCG_tree_wd + '/' + hmm_id + '.fasta', 'a+')
            file_out.write('>' + faa_file_basename + '\n')
            if hmm_name != '':
                seq = str(proteinSequence[hmm_name][hmm_pos1:hmm_pos2])
            file_out.write(str(seq) + '\n')
            file_out.close()

# Call mafft to align all single fasta files with hmms
files = os.listdir(pwd_SCG_tree_wd)
fastaFiles = [i for i in files if i.endswith('.fasta')]
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Running mafft...')
for faa_file_basename in fastaFiles:
    fastaFile1 = '%s/%s' % (pwd_SCG_tree_wd, faa_file_basename)
    fastaFile2 = fastaFile1.replace('.fasta', '_aligned.fasta')
    os.system(pwd_mafft_exe + ' --quiet --maxiterate 1000 --globalpair ' + fastaFile1 + ' > ' + fastaFile2 + ' ; rm ' + fastaFile1)


# concatenating the single alignments
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Concatenating alignments...')
concatAlignment = {}
for element in faa_file_basename_list:
    concatAlignment[element] = ''


# Reading all single alignment files and append them to the concatenated alignment
files = os.listdir(pwd_SCG_tree_wd)
fastaFiles = [i for i in files if i.endswith('.fasta')]
for faa_file_basename in fastaFiles:
    fastaFile = pwd_SCG_tree_wd + '/' + faa_file_basename
    proteinSequence = {}
    alignmentLength = 0
    for seq_record_2 in SeqIO.parse(fastaFile, 'fasta'):
        proteinName = seq_record_2.id
        proteinSequence[proteinName] = str(seq_record_2.seq)
        alignmentLength = len(proteinSequence[proteinName])

    for element in faa_file_basename_list:
        if element in proteinSequence.keys():
            concatAlignment[element] += proteinSequence[element]
        else:
            concatAlignment[element] += '-' * alignmentLength

# writing alignment to file
file_out = open(pwd_combined_alignment_file, 'w')
for element in faa_file_basename_list:
    file_out.write('>' + element + '\n' + concatAlignment[element] + '\n')
file_out.close()

# calling fasttree for tree calculation
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Running fasttree...')
os.system('%s -quiet %s > %s' % (pwd_fasttree_exe, pwd_combined_alignment_file, pwd_newick_tree_file))

# Decomment the two following lines if tree is rooted but should be unrooted
# phyloTree = dendropy.Tree.get(path='phylogenticTree.phy', schema='newick', rooting='force-unrooted')
# dendropy.Tree.write_to_path(phyloTree, 'phylogenticTree_unrooted.phy', 'newick')
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' The built species tree was exported to %s' % newick_tree_file)

###################################################### get cluster #####################################################

# get bin to taxon dict
bin_to_taxon_dict = {}
if taxon_classification_file != None:
    bin_to_taxon_dict = get_rank_assignment_dict(selected_rank, taxon_classification_file)

# read in tree
tree_in = Tree(pwd_newick_tree_file, format=3)

# get sorted leaf node list
leaf_node_list = []
for leaf_node in tree_in:
    leaf_node_list.append(leaf_node.name)
leaf_node_list = sorted(leaf_node_list)

# get distance matrix from tree file
sleep(0.5)
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Get distance matrix from tree')

all_distances_lol = get_distance_matrix(pwd_newick_tree_file)

# turn list of distance list into arrary
all_distances_lol_array = np.array(all_distances_lol)

# get linkage
cluster = linkage(all_distances_lol_array, method='single')

# get maximum distance for clustering
distance_list = []
for each in cluster:
    distance_list.append(each[2])

# get distance cutoff
percentile_for_distances_cutoff = 90
distance_of_percentile = np.percentile(distance_list, percentile_for_distances_cutoff)

if max_d == None:
    max_d = distance_of_percentile
    sleep(0.5)
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Determined distance cutoff is: %s, you can change it with option "-dc"' % float("{0:.2f}".format(max_d)))
else:
    sleep(0.5)
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Distance cutoff specified to %s' % max_d)

# get flat clusters
sleep(0.5)
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Grouping input genomes based on above distance cutoff')
flat_clusters = fcluster(cluster, max_d, criterion='distance')

# get group number
group_index_list = []
for each_index in flat_clusters:
    if int(each_index) not in group_index_list:
        group_index_list.append(each_index)
group_number = len(group_index_list)

# define output file name with grouping included
png_file_group =            '%s_grouping_g%s.png'       % (output_prefix, group_number)
grouping_file =             '%s_grouping_g%s.txt'       % (output_prefix, group_number)
grouping_file_temp =        '%s_grouping_g%s_tmp.file'  % (output_prefix, group_number)
pwd_png_file_group =        '%s/%s'                     % (MetaCHIP_wd, png_file_group)
pwd_grouping_file =         '%s/%s'                     % (MetaCHIP_wd, grouping_file)
pwd_grouping_file_temp =    '%s/%s'                     % (MetaCHIP_wd, grouping_file_temp)

# get grouping file
group_index_list = get_group_index_list()
grouping_file_temp_handle = open(pwd_grouping_file_temp, 'w')
bin_to_grouping_dict = {}
n = 0
for each_leaf in leaf_node_list:
    leaf_cluster_index = int(flat_clusters[n])
    leaf_grouping_id = group_index_list[leaf_cluster_index - 1]
    grouping_file_temp_handle.write('%s,%s\n' % (leaf_grouping_id,each_leaf))
    bin_to_grouping_dict[each_leaf] = leaf_grouping_id
    n += 1
grouping_file_temp_handle.close()

# sort grouping file
os.system('cat %s | sort > %s; rm %s' % (pwd_grouping_file_temp, pwd_grouping_file, pwd_grouping_file_temp))

# report
sleep(0.5)
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Grouping results exported to: %s' % grouping_file)

# calculate full dendrogram
sleep(0.5)
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Get plot for visualization')
if taxon_classification_file != None:
    plot_clustering_dendrogram(cluster, leaf_font_size, get_taxon, max_d, pwd_png_file_group)
else:
    plot_clustering_dendrogram(cluster, leaf_font_size, get_group, max_d, pwd_png_file_group)

# call R
current_wd = os.getcwd()
os.chdir(MetaCHIP_wd)
add_group_to_tree_R_cmd = 'Rscript %s -t %s -g %s > /dev/null' % (add_group_to_tree_R, newick_tree_file, grouping_file)
os.system(add_group_to_tree_R_cmd)
os.chdir(current_wd)

# report done
sleep(0.5)
print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Grouping step done!')