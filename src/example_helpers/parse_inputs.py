import wget 
import zipfile 
import csv 

BV_BRC_METADTA_FTP = "ftp://ftp.bvbrc.org/RELEASE_NOTES/genome_metadata"
NCBI_TAXON_DUMP = "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdmp.zip"


# Download BV-BRC metadata file
print("Downloading BV-BRC metadata")
bv_brc_out = "../../example/downloads/bv_brc_metadata"
wget.download(BV_BRC_METADTA_FTP, out = bv_brc_out)

print("Downloading taxdump zip")
taxo_out = "../../example/downloads/taxdump.zip"
wget.download(NCBI_TAXON_DUMP, out = taxo_out)

print("Extracting taxdump zip...")
with zipfile.ZipFile(taxo_out, 'r') as zip_ref:
    zip_ref.extractall(taxo_out.rstrip("taxdump.zip"))
    
print("Extracting unique host names")
bv_brc_out_unique = "../../example/downloads/bv_brc_unique_hosts.txt"
host_col = "host_name"
with open(bv_brc_out, "r", encoding="utf-8") as in_file, open(bv_brc_out_unique, "w", encoding="utf-8") as out:
    unique_host_names = set([row[host_col].lower() for row in csv.DictReader(in_file, delimiter="\t")])
    print(f"Unique host name: {len(unique_host_names)}")
    out.write("\n".join(unique_host_names))

print("Reading taxo dump file")
taxo_names_out = "../../example/downloads/taxo_names.txt"
with open("../../example/downloads/names.dmp", "r") as in_file, open(taxo_names_out, "w") as out:
    for line in in_file:
        taxo_name = line.split("|")[1].strip()
        out.write(f"{taxo_name}\n")

print("Running algo")
import sys 
sys.path.insert(0, '../')
from heurFuzz import * 
run(bv_brc_out_unique, taxo_names_out, 100, 90, 500, "../../example/bv_brc_taxo_anno.txt")


