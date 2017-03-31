import os
import random
import shutil
import argparse
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import generic_dna
from Bio.SeqUtils.CodonUsage import SynonymousCodons


usage = '''
python3 HgtSIM.py -t transferredGenes.fasta -i 90 -r 1-0-1-1 -d donor2recip.txt -R recipients -x fna
'''

def get_codon_differences(codon_1, codon_2):
    n = 0
    m = 0
    while n < 3:
        if codon_1[n] != codon_2[n]:
            m += 1
        n += 1
    return m


def split_sequence(original_seq):
    n = 0
    original_seq_split = []
    while n+2 < len(original_seq):
        original_seq_split.append(original_seq[n: n+3])
        n += 3
    return original_seq_split


def get_mutant_codon_number(total, ratio):

    ratio_split = ratio.split('-')
    ratio_1_samesense = int(ratio_split[0])  # one base samesense
    ratio_1 = int(ratio_split[1])  # one base non-samesense
    ratio_2 = int(ratio_split[2])  # two bases
    ratio_3 = int(ratio_split[3])  # three bases

    total_unit = (ratio_1_samesense * 1) + (ratio_1 * 1) + (ratio_2 * 2) + (ratio_3 * 3)

    mult_step = total//total_unit

    mutant_codon_number_1 = (ratio_1 * mult_step)
    mutant_codon_number_2 = (ratio_2 * mult_step)
    mutant_codon_number_3 = (ratio_3 * mult_step)
    mutant_codon_number_1_samesense = (total - mutant_codon_number_1 - mutant_codon_number_2 * 2 - mutant_codon_number_3 * 3)
    total_mutant_codon_number = mutant_codon_number_1_samesense + mutant_codon_number_1 + mutant_codon_number_2 + mutant_codon_number_3

    return [mutant_codon_number_1_samesense, mutant_codon_number_1, mutant_codon_number_2, mutant_codon_number_3], total_mutant_codon_number


def get_synonymous_codons(codon):
    for each in SynonymousCodons:
        if codon in SynonymousCodons[each]:
            synonymous_codon_list = [x for x in SynonymousCodons[each] if x != codon]
            return synonymous_codon_list


def get_random_insertion(recipient_sequence, insert_sequence_list, insert_sequence_id_list, common_stop_sequence):

    insert_gene_number = len(insert_sequence_list)
    length = len(recipient_sequence)
    length_list = list(range(1, length))
    random_bases = random.sample(length_list, insert_gene_number)
    random_bases_sorted = sorted(random_bases)

    # get the start and stop points of all sub_sequences
    sub_sequences_list = []
    n = 0
    first_sequence = [1, random_bases_sorted[n]]
    first_sequence_nc = recipient_sequence[0:random_bases_sorted[n]]
    sub_sequences_list.append(first_sequence)
    while n < insert_gene_number - 1:
        current_sequence = [random_bases_sorted[n] + 1, random_bases_sorted[n+1]]
        sub_sequences_list.append(current_sequence)
        n += 1
    last_sequence = [random_bases_sorted[n] + 1, length]
    sub_sequences_list.append(last_sequence)

    # get new sequences
    new_seq = ''
    m = 0
    while m <= insert_gene_number:
        if m == 0:
            new_seq = first_sequence_nc
        if m > 0:
            current_subsequence_start = sub_sequences_list[m][0] - 1
            current_subsequence_stop = sub_sequences_list[m][1]
            current_subsequence = recipient_sequence[current_subsequence_start:current_subsequence_stop]
            current_insert = insert_sequence_list[m - 1]
            current_insert_id = insert_sequence_id_list[m - 1]
            current_stop_seq_start = common_stop_sequence
            current_stop_seq_end = common_stop_sequence
            current_insert_with_stop = '%s%s%s' % (current_stop_seq_start, current_insert, current_stop_seq_end)
            # print(current_insert_id)
            # print('start: %s' % current_stop_seq_start)
            # print('end: %s' % current_stop_seq_end)
            # print('\n')
            new_seq += current_insert_with_stop
            new_seq += current_subsequence
        m += 1

    return new_seq


codons_non_start_stop = ['TTT', 'TTC', 'TTA', 'TCT', 'TCC', 'TCA', 'TCG', 'TAT', 'TAC', 'TGT', 'TGC', 'TGG',
                         'CTT', 'CTC', 'CTA', 'CCT', 'CCC', 'CCA', 'CCG', 'CAT', 'CAC', 'CAA', 'CAG', 'CGT',
                         'CGC', 'CGA', 'CGG', 'ATT', 'ATC', 'ATA', 'ACT', 'ACC', 'ACA', 'ACG', 'AAT', 'AAC',
                         'AAA', 'AAG', 'AGT', 'AGC', 'AGA', 'AGG', 'GTT', 'GTC', 'GTA', 'GTG', 'GCT', 'GCC',
                         'GCA', 'GCG', 'GAT', 'GAC', 'GAA', 'GAG', 'GGT', 'GGC', 'GGA', 'GGG']

codon_to_aa_dict = {'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L', 'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
                    'TAT': 'Y', 'TAC': 'Y', 'TGT': 'C', 'TGC': 'C', 'TGG': 'W', 'CTT': 'L', 'CTC': 'L', 'CTA': 'L',
                    'CTG': 'L', 'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P', 'CAT': 'H', 'CAC': 'H', 'CAA': 'Q',
                    'CAG': 'Q', 'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R', 'ATT': 'I', 'ATC': 'I', 'ATA': 'I',
                    'ATG': 'M', 'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T', 'AAT': 'N', 'AAC': 'N', 'AAA': 'K',
                    'AAG': 'K', 'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R', 'GTT': 'V', 'GTC': 'V', 'GTA': 'V',
                    'GTG': 'V', 'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A', 'GAT': 'D', 'GAC': 'D', 'GAA': 'E',
                    'GAG': 'E', 'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G', 'TAA': '*', 'TAG': '*', 'TGA': '*', }


################################################# input #################################################

parser = argparse.ArgumentParser()

parser.add_argument('-t',
                    required=True,
                    help='Sequences of genes want to be transferred (multi-fasta format)')

parser.add_argument('-i',
                    required=True,
                    type=int,
                    help='the identity between input and mutant sequences')

parser.add_argument('-r',
                    required=True,
                    default='1-0-1-1',
                    help='ratio of mutation types')

parser.add_argument('-d',
                    required=True,
                    help='direction of transfers')

parser.add_argument('-f',
                    required=True,
                    help='recipient genome folder')

parser.add_argument('-x',
                    required=False,
                    default='fna',
                    help='extension of recipient genomes')

parser.add_argument('-s',
                    required=False,
                    default='TAGATGAGTGATTAGTTAGTTA',
                    help='universal transcription termination sequence')

# parser.add_argument('-tt',
#                     required=False,
#                     default='orf',
#                     help='the type of sequences want to be transfered, either ORFs (orf, default) or randomly selected sequences (norf)')

args = vars(parser.parse_args())
input_seq_file_name = args['t']
mutant_identity = args['i']
ratio = args['r']
transfer_profile_file = args['d']
recipients_genome_extension = args['x']
common_stop_sequence = args['s']
recipients_folder = args['f']
if recipients_folder[-1] == '/':
    recipients_folder = recipients_folder[:-1]

#########################################################################################################


# define output file name
wd = os.getcwd()
output_folder =             '%s/outputs_%s_%s'                      % (wd, mutant_identity, ratio)
input_seq_file =            '%s/%s'                                 % (wd, input_seq_file_name)
input_aa_seq_file =         '%s/input_sequence_aa.fasta'            % output_folder
output_seq_file =           '%s/input_sequence_mutant_nc.fasta'     % output_folder
output_aa_seq_file =        '%s/input_sequence_mutant_aa.fasta'     % output_folder
output_blast =              '%s/blast_results_nc.txt'               % output_folder
output_blast_aa =           '%s/blast_results_aa.txt'               % output_folder
simulate_report_file_temp = '%s/simulation_report_temp.txt'         % output_folder
simulate_report_file =      '%s/simulation_report.txt'              % output_folder
pwd_transfers =             '%s/%s'                                 % (wd, transfer_profile_file)
pwd_recipients_folder =     '%s/%s'                                 % (wd, recipients_folder)
pwd_output_folder =         '%s/Genomes_with_transfers'             % output_folder


# create random mutation output folder
if os.path.isdir(output_folder):
    shutil.rmtree(output_folder)
    os.mkdir(output_folder)
    if os.path.isdir(output_folder):
        shutil.rmtree(output_folder)
        os.mkdir(output_folder)
    os.mkdir(pwd_output_folder)
else:
    os.mkdir(output_folder)
    os.mkdir(pwd_output_folder)

simulate_report = open(simulate_report_file_temp, 'w')
input_aa_handle = open(input_aa_seq_file, 'w')
output_handle = open(output_seq_file, 'w')
output_aa_handle = open(output_aa_seq_file, 'w')
all_sequence_id_list = []
sequence_length_dict_nc = {}
sequence_length_dict_aa = {}
n = 0

for each_seq in SeqIO.parse(input_seq_file, 'fasta'):
    input_seq = str(each_seq.seq)
    seq_length = len(input_seq)
    print('Processing: %s, length: %s' % (each_seq.id, seq_length))
    all_sequence_id_list.append(each_seq.id)
    sequence_length_dict_nc[each_seq.id] = seq_length
    sequence_length_dict_aa[each_seq.id + '_aa'] = int(seq_length/3 - 1)

    # get translated input sequences
    input_seq_object = Seq(str(each_seq.seq))
    input_seq_aa_object = input_seq_object.translate()
    input_seq_aa_record = SeqRecord(input_seq_aa_object)
    input_seq_aa_record.id = each_seq.id + '_aa'
    input_seq_aa_record.description = ''
    SeqIO.write(input_seq_aa_record, input_aa_handle, 'fasta')

    # get total number of mutant codons according to defined ratio
    mutation_bps = (seq_length * (100 - mutant_identity)) // 100
    mutant_codon_number_list, mutant_codon_number = get_mutant_codon_number(mutation_bps, ratio)

    # split input sequence
    input_seq_split = split_sequence(input_seq)

    # index split input sequence
    input_seq_split_index = list(range(0, len(input_seq_split), 1))

    # randomly select defined number of codons from splitted input sequences
    input_seq_split_index_radom = random.sample(input_seq_split_index[1:-1], mutant_codon_number)

    # get codons for each types of mutation
    codons_for_samesense_mutation = input_seq_split_index_radom[:mutant_codon_number_list[0]]
    codons_for_mutation_1_bases = input_seq_split_index_radom[mutant_codon_number_list[0] : mutant_codon_number_list[0] + mutant_codon_number_list[1]]
    codons_for_mutation_2_bases = input_seq_split_index_radom[mutant_codon_number_list[0] + mutant_codon_number_list[1] : mutant_codon_number_list[0] + mutant_codon_number_list[1] + mutant_codon_number_list[2]]
    codons_for_mutation_3_bases = input_seq_split_index_radom[mutant_codon_number_list[0] + mutant_codon_number_list[1] + mutant_codon_number_list[2]:]
    mutation_type_list = [codons_for_samesense_mutation, codons_for_mutation_1_bases, codons_for_mutation_2_bases, codons_for_mutation_3_bases]

    # if 'TGG' in codons_for_samesense_mutation, move it to codons_for_mutation_1_bases
    codons_for_samesense_mutation_non_TGG_ATG = []
    for each_codon_for_samesense_mutation in codons_for_samesense_mutation:
        if input_seq_split[each_codon_for_samesense_mutation] not in ['TGG', 'tgg', 'UGG', 'ugg', 'ATG', 'atg', 'UTG', 'utg']:
            codons_for_samesense_mutation_non_TGG_ATG.append(each_codon_for_samesense_mutation)
        else:
            codons_for_mutation_1_bases.append(each_codon_for_samesense_mutation)

    simulate_report.write('\n\n%s:\n' % each_seq.id)
    simulate_report.write('One point mutation (same-sense):\t%s\n' % len(codons_for_samesense_mutation_non_TGG_ATG))
    simulate_report.write('One point mutation (non-same-sense):\t%s\n' % len(codons_for_mutation_1_bases))
    simulate_report.write('Two points mutation:\t%s\n' % len(codons_for_mutation_2_bases))
    simulate_report.write('Three points mutation:\t%s\n' % len(codons_for_mutation_3_bases))

    total_mutations_bp = len(codons_for_samesense_mutation_non_TGG_ATG) + \
                         len(codons_for_mutation_1_bases) + \
                         2*len(codons_for_mutation_2_bases) + \
                         3*len(codons_for_mutation_3_bases)

    simulate_report.write('Length of input sequence (bp): %s\n' % len(input_seq))
    simulate_report.write('Mutation types ratio:\t%s\t(One (same-sense) : One (non-same-sense) : Two : Three)\n' % ratio)
    simulate_report.write('Total mutations (bp):\t%s + %s + (2 x %s) + (3 x %s) = %s\n\n' % (len(codons_for_samesense_mutation_non_TGG_ATG),
                                                                                             len(codons_for_mutation_1_bases),
                                                                                             len(codons_for_mutation_2_bases),
                                                                                             len(codons_for_mutation_3_bases),
                                                                                             total_mutations_bp))

    # simulate same-sense mutation
    for each_codon_for_samesense_mutation in codons_for_samesense_mutation_non_TGG_ATG:
        current_codon_for_samesense_mutation = input_seq_split[each_codon_for_samesense_mutation]
        current_codon_for_samesense_mutation_for_report = current_codon_for_samesense_mutation
        current_codon_for_samesense_mutation_synonymous_codons = get_synonymous_codons(current_codon_for_samesense_mutation)
        current_codon_synonymous_codons_1bp = []
        for each in current_codon_for_samesense_mutation_synonymous_codons:
            if get_codon_differences(each, current_codon_for_samesense_mutation) == 1:
                current_codon_synonymous_codons_1bp.append(each)

        current_codon_synonymous_codons_1bp_random = random.choice(current_codon_synonymous_codons_1bp)
        input_seq_split[each_codon_for_samesense_mutation] = current_codon_synonymous_codons_1bp_random
        simulate_report.write('%s\tOne point mutation (same-sense)\t%s-%sbp\t%s(%s)\t%s(%s)\n' % (each_seq.id, (3 * each_codon_for_samesense_mutation + 1),
                                                                                                  (3 * each_codon_for_samesense_mutation + 3),
                                                                                                  current_codon_for_samesense_mutation,
                                                                                                  codon_to_aa_dict[current_codon_for_samesense_mutation],
                                                                                                  current_codon_synonymous_codons_1bp_random,
                                                                                                  codon_to_aa_dict[current_codon_synonymous_codons_1bp_random]))

    # simulate mutation with 1bp difference
    for each_codon_for_1_base_mutation in codons_for_mutation_1_bases:
        current_codon_for_1_base_mutation = input_seq_split[each_codon_for_1_base_mutation]
        current_1_diff_codons_all = []
        for each_codon in codons_non_start_stop:
            if get_codon_differences(current_codon_for_1_base_mutation, each_codon) == 1:
                current_1_diff_codons_all.append(each_codon)
        current_1_diff_codons_synonymous = get_synonymous_codons(current_codon_for_1_base_mutation)
        current_1_diff_codons_non_synonymous = []
        for each_codon in current_1_diff_codons_all:
            if each_codon not in current_1_diff_codons_synonymous:
                current_1_diff_codons_non_synonymous.append(each_codon)
        current_1_diff_codons_non_synonymous_random = random.choice(current_1_diff_codons_non_synonymous)
        input_seq_split[each_codon_for_1_base_mutation] = current_1_diff_codons_non_synonymous_random
        simulate_report.write('%s\tOne point mutation (non-same-sense)\t%s-%sbp\t%s(%s)\t%s(%s)\n' % (each_seq.id, (3 * each_codon_for_1_base_mutation + 1),
                                                                                                      (3 * each_codon_for_1_base_mutation + 3),
                                                                                                      current_codon_for_1_base_mutation,
                                                                                                      codon_to_aa_dict[current_codon_for_1_base_mutation],
                                                                                                      current_1_diff_codons_non_synonymous_random,
                                                                                                      codon_to_aa_dict[current_1_diff_codons_non_synonymous_random]))

    # simulate mutation with 2bp differences
    for each_codon_for_2_base_mutation in codons_for_mutation_2_bases:
        current_codon_for_2_base_mutation = input_seq_split[each_codon_for_2_base_mutation]
        current_2_diff_codons_all = []
        for each_codon in codons_non_start_stop:
            if get_codon_differences(current_codon_for_2_base_mutation, each_codon) == 2:
                current_2_diff_codons_all.append(each_codon)
        current_2_diff_codons_all_random = random.choice(current_2_diff_codons_all)
        input_seq_split[each_codon_for_2_base_mutation] = current_2_diff_codons_all_random
        simulate_report.write('%s\tTwo points mutation\t%s-%sbp\t%s(%s)\t%s(%s)\n' % (each_seq.id, (3 * each_codon_for_2_base_mutation + 1),
                                                                                      (3 * each_codon_for_2_base_mutation + 3),
                                                                                      current_codon_for_2_base_mutation,
                                                                                      codon_to_aa_dict[current_codon_for_2_base_mutation],
                                                                                      current_2_diff_codons_all_random,
                                                                                      codon_to_aa_dict[current_2_diff_codons_all_random]))

    # simulate mutation with 3bp differences
    for each_codon_for_3_base_mutation in codons_for_mutation_3_bases:
        current_codon_for_3_base_mutation = input_seq_split[each_codon_for_3_base_mutation]
        current_3_diff_codons_all = []
        for each_codon in codons_non_start_stop:
            if get_codon_differences(current_codon_for_3_base_mutation, each_codon) == 3:
                current_3_diff_codons_all.append(each_codon)
        current_3_diff_codons_all_random = random.choice(current_3_diff_codons_all)
        input_seq_split[each_codon_for_3_base_mutation] = current_3_diff_codons_all_random
        simulate_report.write('%s\tThree points mutation\t%s-%sbp\t%s(%s)\t%s(%s)\n' % (each_seq.id, (3 * each_codon_for_3_base_mutation + 1),
                                                                                        (3 * each_codon_for_3_base_mutation + 3),
                                                                                        current_codon_for_3_base_mutation,
                                                                                        codon_to_aa_dict[current_codon_for_3_base_mutation],
                                                                                        current_3_diff_codons_all_random,
                                                                                        codon_to_aa_dict[current_3_diff_codons_all_random]))

    # write into output files
    new_seq = ''.join(input_seq_split)
    new_seq_object = Seq(new_seq, generic_dna)
    new_seq_object_aa = new_seq_object.translate()
    new_seq_record = SeqRecord(new_seq_object)
    new_seq_record_aa = SeqRecord(new_seq_object_aa)
    new_seq_record.id = each_seq.id + ''
    new_seq_record_aa.id = each_seq.id + '_aa'
    new_seq_record.description = ''
    new_seq_record_aa.description = ''
    SeqIO.write(new_seq_record, output_handle, 'fasta')
    SeqIO.write(new_seq_record_aa, output_aa_handle, 'fasta')
    n += 1

input_aa_handle.close()
output_handle.close()
output_aa_handle.close()
simulate_report.close()


# run blastn between input and mutant sequences
print('Running BlastN between input and mutant sequences')
blast_parameters_outfmt = ' -evalue 1e-5 -task blastn'
blast_parameters_outfmt_6 = ' -evalue 1e-5 -outfmt 6 -task blastn'
command_blast = 'blastn -query %s -subject %s -out %s%s' % (input_seq_file, output_seq_file, output_blast, blast_parameters_outfmt_6)
os.system(command_blast)

# run blastp between input and mutant sequences
print('Running BlastP between input and mutant sequences')
blast_parameters_outfmt_aa = ' -evalue 1e-5 -task blastp'
blast_parameters_outfmt_6_aa = ' -evalue 1e-5 -outfmt 6 -task blastp'
command_blast_aa = 'blastp -query %s -subject %s -out %s%s' % (input_aa_seq_file, output_aa_seq_file, output_blast_aa, blast_parameters_outfmt_6_aa)
os.system(command_blast_aa)

# put the results of blastn and blastp together
overall_blast_results = '%s/blast_results_overall.txt' % output_folder
overall_blast_results_handle = open(overall_blast_results, 'w')

blastn_results = open(output_blast)
obtained_mutant_list = []
mutant_identity_dict_nc = {}
for each in blastn_results:
    each_split = each.strip().split('\t')
    query = each_split[0]
    subject = each_split[1]
    identity = float(each_split[2])
    identity = float("{0:.1f}".format(float(identity)))
    alignment_length = int(each_split[3])
    alignment_percent = alignment_length/sequence_length_dict_nc[query]
    if (query in subject) and (alignment_percent > 0.8):
        obtained_mutant_list.append(query)
        mutant_identity_dict_nc[query] = identity

blastp_results = open(output_blast_aa)
mutant_identity_dict_aa = {}
for each_aa in blastp_results:
    each_split_aa = each_aa.strip().split('\t')
    query_aa = each_split_aa[0]
    query_non_aa = query_aa[:-3]
    subject_aa = each_split_aa[1]
    identity_aa = float(each_split_aa[2])
    identity_aa = float("{0:.1f}".format(float(identity_aa)))
    alignment_length_aa = int(each_split_aa[3])
    alignment_percent_aa = alignment_length_aa / sequence_length_dict_aa[query_aa]
    if (query_aa in subject_aa) and (alignment_percent_aa > 0.8):
        mutant_identity_dict_aa[query_non_aa] = identity_aa


overall_blast_results_handle.write('Sequence\tIden_nc\tIden_aa\n')
for each in all_sequence_id_list:
    if (each in mutant_identity_dict_nc) and (each in mutant_identity_dict_aa):
        overall_blast_results_handle.write('%s\t%s\t%s\n' % (each, mutant_identity_dict_nc[each], mutant_identity_dict_aa[each]))
    else:
        overall_blast_results_handle.write('%s: No similarity was found between %s and its mutant, Please try again with a different ratio or with a higher identity cutoff.\n' % (each, each))
overall_blast_results_handle.close()


pwd_sequences_file = output_seq_file

# read insert sequences into a list
transfers = open(pwd_transfers)
for each in transfers:
    each_split = each.strip().split(',')
    recipient_genome_id = each_split[0]
    insert_sequence_id_list_unorder = each_split[1:]
    pwd_recipient_genome = '%s/%s.%s' % (pwd_recipients_folder, recipient_genome_id, recipients_genome_extension)
    recipient_genome = SeqIO.read(pwd_recipient_genome, 'fasta')
    recipient_genome_nc = str(recipient_genome.seq)

    # read insert sequences into list
    combined_ffn_handle = SeqIO.parse(pwd_sequences_file, 'fasta')
    insert_sequence_id_list = []
    insert_sequence_seq_list = []
    for each_gene in combined_ffn_handle:
        if each_gene.id in insert_sequence_id_list_unorder:
            insert_sequence_id_list.append(each_gene.id)
            insert_sequence_seq_list.append(str(each_gene.seq))

    new_seq = get_random_insertion(recipient_genome_nc, insert_sequence_seq_list, insert_sequence_id_list, common_stop_sequence)
    new_seq_record = SeqRecord(Seq(new_seq, IUPAC.unambiguous_dna), id=recipient_genome_id, description='')
    pwd_new_seq_file = '%s/%s.%s' % (pwd_output_folder, recipient_genome_id, recipients_genome_extension)
    new_seq_file_handle = open(pwd_new_seq_file, 'w')
    SeqIO.write(new_seq_record, new_seq_file_handle, 'fasta')
    new_seq_file_handle.close()


# delete temporary files
os.remove(output_blast)
os.remove(output_blast_aa)
os.system('cat %s %s > %s' % (overall_blast_results,simulate_report_file_temp, simulate_report_file))
os.remove(overall_blast_results)
os.remove(simulate_report_file_temp)
