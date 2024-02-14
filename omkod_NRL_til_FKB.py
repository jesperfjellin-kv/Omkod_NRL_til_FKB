input_file_path = 'NRL_Avvik.sos'
output_file_path = 'NRL_Avvik_omkodet.sos'

mappings = {
    "..OBJTYPE NrlLuftspenn": "..OBJTYPE Trase",
    "..OBJTYPE NrlMast": "..OBJTYPE Mast",
    "..HØYDEREFERANSE": "..HREF"
}

unwanted_attributes = {
    "..VERIFISERTRAPPORTERINGSNØYAKTIGHET",
    "..HISTORISKNRLID",
    "..STATUS",
    "..REGISTRERINGSDATO",
    "...LUFTFARTSHINDERID",
    "...GEOMETRIID",
    "..NAVN",
    "..VERTIKALAVSTAND",
    "..OPPDATERINGSDATO",
    "..MASTTYPE",
    "..IDENTIFIKASJON",
    "...LOKALID",
    "...VERSJONID",
    "..LUFTSPENNTYPE",
    "..INFORMASJON",
    "..LUFTFARTSHINDERLYSSETTING",
    "..EIER",
    "..PRODUSENT"
}

def translate_line(line, mappings):
    for old_value, new_value in mappings.items():
        if old_value in line:
            line = line.replace(old_value, new_value)
    return line

def is_line_unwanted(line, unwanted_attributes):
    for attribute in unwanted_attributes:
        if attribute in line:
            return True
    return False

def read_and_modify_head_section(lines):
    modified_lines = []
    in_head = False
    sosi_versjon_present = False
    sosi_nivå_present = False
    vert_datum_present = False

    for line in lines:
        if '.HODE' in line:
            in_head = True
        if in_head:
            if '..SOSI-VERSJON' in line:
                sosi_versjon_present = True
                if '5.0' not in line:
                    line = '..SOSI-VERSJON 5.0\n'
            elif '..SOSI-NIVÅ' in line:
                sosi_nivå_present = True
            elif '...VERT-DATUM' in line:
                vert_datum_present = True
            if '..TRANSPAR' in line:
                in_head = False
                if not vert_datum_present:
                    line += '...VERT-DATUM NN2000\n'
        modified_lines.append(line)

    if not sosi_versjon_present:
        modified_lines.insert(1, '..SOSI-VERSJON 5.0\n')
    if not sosi_nivå_present:
        modified_lines.insert(2, '..SOSI-NIVÅ 3\n')

    return modified_lines

def apply_mappings_and_filter(lines, mappings, unwanted_attributes):
    processed_lines = []
    for line in lines:
        if not is_line_unwanted(line, unwanted_attributes):
            line = translate_line(line, mappings)
            processed_lines.append(line)
    return processed_lines

def modify_and_process_file(input_file_path, output_file_path, mappings, unwanted_attributes):
    with open(input_file_path, 'r', encoding='utf-8') as input_file:
        lines = input_file.readlines()

    # Modify the .HODE section first
    modified_lines = read_and_modify_head_section(lines)

    # Then apply mappings and filter unwanted attributes for the entire file
    final_lines = apply_mappings_and_filter(modified_lines, mappings, unwanted_attributes)

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for line in final_lines:
            output_file.write(line)

modify_and_process_file(input_file_path, output_file_path, mappings, unwanted_attributes)
print("Omkodet egenskaper skrevet til: ", output_file_path)
