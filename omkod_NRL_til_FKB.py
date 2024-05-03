import tkinter as tk
from tkinter import filedialog
import re
import sys

def check_datafangstdato_format(lines):
    """
    Sjekker at ..DATAFANGSTDATO er i riktig format (..DATAFANGSTDATO YYYYMMDD)
    """
    datafangstdato_pattern = re.compile(r'^\.\.DATAFANGSTDATO \d{8}$')  # Regex 

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('..DATAFANGSTDATO'):
            if not datafangstdato_pattern.match(stripped_line):
                print("Incorrect format found:", stripped_line)

def modify_and_process_file(input_file_path, output_file_path, mappings, unwanted_attributes, new_attributes):
    with open(input_file_path, 'r', encoding='utf-8') as input_file:
        lines = input_file.readlines()

    modified_lines = read_and_modify_head_section(lines)
    modified_lines = apply_mappings_and_filter(modified_lines, mappings, unwanted_attributes)
    modified_lines = remove_unwanted_objects(modified_lines)
    modified_lines = remove_registreringsdato_if_datafangstdato_present(modified_lines)
    modified_lines = convert_and_shorten_registreringsdato(modified_lines)
    modified_lines = insert_new_attributes_under_objects(modified_lines, new_attributes)
    modified_lines = missing_kvalitet(modified_lines)
    modified_lines = ensure_belysning_for_masts(modified_lines)

    check_datafangstdato_format(modified_lines)

    if not modified_lines[-1].strip().endswith(".SLUTT"):
        modified_lines.append(".SLUTT\n")

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.writelines(modified_lines)

    print("Omkodet egenskaper skrevet til:", output_file_path)

def read_and_modify_head_section(lines):
    """
    Leser og modifiserer hodet av SOSI-filen for å sikre riktig versjon og kataloginformasjon.
    """
    modified_lines = []
    in_hode = False
    sosi_version_found = False
    objektkatalog_found = False
    hode_index = -1

    for line in lines:
        if '.HODE' in line:
            in_hode = True
            hode_index = len(modified_lines)
        elif in_hode and (line.startswith('.PUNKT') or line.startswith('.KURVE')):
            in_hode = False
        elif in_hode:
            if '..SOSI-VERSJON' in line:
                sosi_version_found = True
                if '5.0' not in line:
                    line = '..SOSI-VERSJON 5.0\n'
            if '..OBJEKTKATALOG' in line:
                objektkatalog_found = True
                if 'FKBLedning 5.0' not in line:
                    line = '..OBJEKTKATALOG FKBLedning 5.0\n'

        modified_lines.append(line)

    if not sosi_version_found and hode_index != -1:
        modified_lines.insert(hode_index + 1, '..SOSI-VERSJON 5.0\n')
    if not objektkatalog_found and hode_index != -1:
        insert_index = hode_index + 1 if not sosi_version_found else hode_index + 2
        modified_lines.insert(insert_index, '..OBJEKTKATALOG FKBLedning 5.0\n')

    return modified_lines

def apply_mappings_and_filter(lines, mappings, unwanted_attributes):
    """
    Endrer eksisterende attributter og filtrerer ut uønskede attributter.
    """
    processed_lines = []
    for line in lines:
        if not is_line_unwanted(line, unwanted_attributes):
            line = translate_line(line, mappings)
            processed_lines.append(line)
    return processed_lines

def is_line_unwanted(line, unwanted_attributes):
    """
    Sjekker om en linje inneholder attributter som er uønskede.
    """
    line_lower = line.lower()  
    for attribute in unwanted_attributes:
        if attribute.lower() in line_lower:
            return True
    return False

def translate_line(line, mappings):
    """
    Oversetter linjer basert på forhåndsdefinerte mappinger.
    """
    for old_value, new_value in mappings.items():
        line = re.sub(re.escape(old_value), lambda match: new_value, line, flags=re.IGNORECASE)
    return line

def remove_registreringsdato_if_datafangstdato_present(lines):
    """
    Fjerner registreringsdato fra objekter hvis datafangstdato er tilstede.
    """
    processed_lines = []
    current_object = []
    has_datafangstdato = False
    has_registreringsdato = False
    registreringsdato_index = -1

    for line in lines:
        if line.startswith('.PUNKT') or line.startswith('.KURVE') or line.strip() == '':
            if current_object:
                if has_datafangstdato and has_registreringsdato:
                    current_object.pop(registreringsdato_index)
                elif has_registreringsdato:
                    current_object[registreringsdato_index] = '..DATAFANGSTDATO ' + current_object[registreringsdato_index].split()[1].upper()
                for i, obj_line in enumerate(current_object):
                    if '..DATAFANGSTDATO' in obj_line:
                        current_object[i] = obj_line.upper()
                processed_lines.extend(current_object)
                if line.strip() == '':
                    processed_lines.append('\n')
                current_object = []
                has_datafangstdato = False
                has_registreringsdato = False
                registreringsdato_index = -1
        current_object.append(line)
        if '..datafangstdato' in line:
            has_datafangstdato = True
            current_object[-1] = line.upper()
        if '..registreringsdato' in line:
            has_registreringsdato = True
            registreringsdato_index = len(current_object) - 1

    if current_object:
        if has_datafangstdato and has_registreringsdato:
            current_object.pop(registreringsdato_index)
        elif has_registreringsdato:
            current_object[registreringsdato_index] = '..DATAFANGSTDATO ' + current_object[registreringsdato_index].split()[1].upper()
        for i, obj_line in enumerate(current_object):
            if '..DATAFANGSTDATO' in obj_line:
                current_object[i] = obj_line.upper()
        processed_lines.extend(current_object)

    return processed_lines

def convert_and_shorten_registreringsdato(lines):
    """
    Konverterer ..REGISTRERINGSDATO til ..DATAFANGSTDATO og forkorter datoformatet til YYYYMMDD (hvis objektet ikke allerede
    har en ..DATAFANGSTDATO attributt)
    """
    processed_lines = []
    current_object = []
    object_started = False
    datafangstdato_present = False

    date_pattern = re.compile(r'(\d{14})')  # Mønster for å finne datoer i formatet YYYYMMDDHHMMSS

    for line in lines:
        if line.startswith('.PUNKT') or line.startswith('.KURVE') or line.strip() == '':
            if current_object:
                if not datafangstdato_present:
                    new_object_lines = []
                    for obj_line in current_object:
                        if '..REGISTRERINGSDATO' in obj_line:
                            date_match = date_pattern.search(obj_line)
                            if date_match:
                                date = date_match.group(0)[:8]  # YYYYMMDD
                                new_line = f'..DATAFANGSTDATO {date}'
                                remainder = obj_line[date_match.end():].strip()  # Fjerner tallverdi etter 8 siffer
                                new_object_lines.append(new_line + '\n')
                                if remainder:
                                    new_object_lines.append(remainder + '\n')
                            else:
                                new_object_lines.append(obj_line)  # Safeguard hvis regex ikke finner dato
                        else:
                            new_object_lines.append(obj_line)
                    processed_lines.extend(new_object_lines)
                else:
                    processed_lines.extend(current_object)
                if line.strip() == '':
                    processed_lines.append('\n')
                current_object = []
                object_started = False
                datafangstdato_present = False
        if line.strip() != '':
            if not object_started:
                current_object = []
                object_started = True
            current_object.append(line)
            if '..DATAFANGSTDATO' in line:
                datafangstdato_present = True
                date_match = date_pattern.search(line)
                if date_match:
                    date = date_match.group(0)[:8]  
                    current_object[-1] = f'..DATAFANGSTDATO {date}\n'
                    remaining_text = line[date_match.end():].strip()
                    if remaining_text:
                        current_object.append(remaining_text + '\n')
    if current_object:
        if not datafangstdato_present:
            new_object_lines = []
            for obj_line in current_object:
                if '..REGISTRERINGSDATO' in obj_line:
                    date_match = date_pattern.search(obj_line)
                    if date_match:
                        date = date_match.group(0)[:8]  
                        new_line = f'..DATAFANGSTDATO {date}'
                        remainder = obj_line[date_match.end():].strip()  
                        new_object_lines.append(new_line + '\n')
                        if remainder:
                            new_object_lines.append(remainder + '\n')
                    else:
                        new_object_lines.append(obj_line)  # Safeguard hvis regex ikke finner dato
                else:
                    new_object_lines.append(obj_line)
            processed_lines.extend(new_object_lines)
        else:
            processed_lines.extend(current_object)
    return processed_lines


def insert_new_attributes_under_objects(lines, new_attributes):
    """
    Setter inn nye attributter under objektdefinisjoner basert på objekttype.
    """
    modified_lines = []
    for line in lines:
        modified_lines.append(line)
        if line.strip().startswith('..OBJTYPE'):
            for new_attr in new_attributes:
                if new_attr not in line:
                    modified_lines.append("\n" + new_attr + "\n")
    return modified_lines

def remove_unwanted_objects(lines):
    """
    Fjerner hele objekter basert på spesifikke kriterier, som objekttype.
    """
    processed_lines = []
    current_object = []
    remove_current_object = False

    for line in lines:
        if line.startswith('.PUNKT') or line.startswith('.KURVE') or (line.strip() == '' and current_object):
            if not remove_current_object:
                processed_lines.extend(current_object)
                if line.strip() == '':
                    processed_lines.append('\n')  

            current_object = []
            remove_current_object = False

        current_object.append(line)

        if '..objtype' in line.lower() and 'nrlpunkt' in line.lower():
            # Fjerner alle instanser av objektet nrlpunkt
            remove_current_object = True

    if current_object and not remove_current_object:
        processed_lines.extend(current_object)

    return processed_lines

def capitalize_key_only(line):
    """
    Kapitaliserer nøkkelord i en linje mens resten av innholdet forblir uendret.
    """
    parts = line.split(maxsplit=1)  
    if len(parts) == 2:  
        parts[0] = parts[0].upper()  
        return ' '.join(parts)  
    return line.upper()  

def missing_kvalitet(lines):
    """
    Sjekker og legger til manglende kvalitetsattributter i objekter.
    """
    modified_lines = []
    current_object_lines = []
    kvalitet_present = False
    in_kvalitet_block = False

    for line in lines:
        if line.strip().startswith('.PUNKT') or line.strip().startswith('.KURVE'):
            if current_object_lines:
                if kvalitet_present:
                    current_object_lines = [capitalize_key_only(line) if line.strip().startswith('...') else line for line in current_object_lines]
                modified_lines.extend(current_object_lines)
            current_object_lines = [line]
            kvalitet_present = False
            in_kvalitet_block = False
        else:
            if line.strip().startswith('..KVALITET'):
                kvalitet_present = True
                in_kvalitet_block = True
            elif line.strip().startswith('..') and not line.strip().startswith('...'):
                if in_kvalitet_block:
                    kvalitet_present = False
                    in_kvalitet_block = False
                    current_object_lines = [capitalize_key_only(line) if line.strip().startswith('...') else line for line in current_object_lines]
            elif in_kvalitet_block and line.strip().startswith('...'):
                line = capitalize_key_only(line) 

            current_object_lines.append(line)

    if current_object_lines:
        if kvalitet_present:
            current_object_lines = [capitalize_key_only(line) if line.strip().startswith('...') else line for line in current_object_lines]
        modified_lines.extend(current_object_lines)

    return modified_lines

def insert_kvalitet_section(object_lines):
    """
    Setter inn standard kvalitetsseksjon under objekttyper som mangler dette.
    """
    kvalitet_section = [
        "..KVALITET\n",
        "...DATAFANGSTMETODE DIG\n",
        "...NØYAKTIGHET 200\n",
        "...DATAFANGSTMETODEHØYDE GEN\n",
        "...H-NØYAKTIGHET 200\n",
        "...SYNBARHET 0\n"
    ]  
    objtype_index = next((i for i, line in enumerate(object_lines) if '..OBJTYPE' in line), None)
    if objtype_index is not None:
        object_lines[objtype_index+1:objtype_index+1] = kvalitet_section

def ensure_belysning_for_masts(lines):
    """
    Sørger for at mastobjekter har korrekt belysningsattributter.
    """
    modified_lines = []
    current_object_lines = []
    is_mast = False
    belysning_present = False

    for line in lines:
        if line.strip().startswith('.PUNKT'):
            if current_object_lines:
                if is_mast and not belysning_present:
                    for i, obj_line in enumerate(current_object_lines):
                        if '..OBJTYPE Mast' in obj_line:
                            current_object_lines.insert(i + 1, "..BELYSNING NEI\n")
                            break
                modified_lines.extend(current_object_lines)
                
            current_object_lines = [line]
            is_mast = '..OBJTYPE Mast' in line
            belysning_present = False
        else:
            if '..OBJTYPE Mast' in line:
                is_mast = True
            if '..BELYSNING' in line:
                belysning_present = True
            current_object_lines.append(line)

    if current_object_lines and is_mast and not belysning_present:
        for i, obj_line in enumerate(current_object_lines):
            if '..OBJTYPE Mast' in obj_line:
                current_object_lines.insert(i + 1, "..BELYSNING NEI\n")
                break
    modified_lines.extend(current_object_lines)

    return modified_lines

def insert_belysning_section(object_lines):
    """
    Setter inn en standard belysningsseksjon under mastobjekter som mangler dette.
    """
    belysning_line = "..BELYSNING NEI\n" 
    objtype_index = next((i for i, line in enumerate(object_lines) if '..OBJTYPE Mast' in line), None)
    if objtype_index is not None:
        object_lines.insert(objtype_index + 1, belysning_line)

mappings = {
    "..OBJTYPE NrlLuftspenn": "..OBJTYPE Trase",
    "..OBJTYPE NrlLinje": "..OBJTYPE Trase",
    "..OBJTYPE NrlMast": "..OBJTYPE Mast",
    "..HØYDEREFERANSE": "..HREF",
    "...NØYAKTIGHETHØYDE": "...H-NØYAKTIGHET"
}

unwanted_attributes = {
    "..VERIFISERTRAPPORTERINGSNØYAKTIGHET",
    "..HISTORISKNRLID",
    "..STATUS",
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
    "..PRODUSENT",
    "..MATERIALE",
    "..HORISONTALAVSTAND",
    "..linjeType",
    "..luftfartshindermerking"
}

new_attributes = [
    "..LEDNINGSNETTVERKSTYPE ukjent",
    "..MEDIUM T"
]

def main(resultatkat):
    input_file_path = resultatkat + '\\NRL_Avvik.sos'
    output_file_path = resultatkat + '\\NRL_Avvik_omkodet.sos'
    modify_and_process_file(input_file_path, output_file_path, mappings, unwanted_attributes, new_attributes)
    print("Omkodet egenskaper skrevet til:", output_file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)

    resultatkat = sys.argv[1]
    main(resultatkat)