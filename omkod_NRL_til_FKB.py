''' Ting som må fikses: et par objekter mangler får ikke ..KVALITET lagt på.
Mast skal ha ..BELYSNING JA/NEI, hva legger vi på som dummyverdi?'''


input_file_path = 'NRL_Avvik.sos'
output_file_path = 'NRL_Avvik_omkodet.sos'

mappings = {
    "..OBJTYPE NrlLuftspenn": "..OBJTYPE Trase",
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
    "..HORISONTALAVSTAND"
}

new_attributes = [ 
    "..LEDNINGSNETTVERKSTYPE ukjent",
    "..MEDIUM T"
]

required_attributes = {
    "..TRANSPAR": None,  
    "...KOORDSYS": "..TRANSPAR",  
    "...ORIGO-NØ": "..TRANSPAR",  
    "...ENHET": "..TRANSPAR",  
    "...VERT-DATUM": "..TRANSPAR"  
}

'''Mapper NRL egenskaper til FKB egenskaper'''
def translate_line(line, mappings):
    for old_value, new_value in mappings.items():
        if old_value in line:
            line = line.replace(old_value, new_value)
    return line

'''Fjerner NRL egenskaper som ikke skal være i FKB'''
def is_line_unwanted(line, unwanted_attributes):
    for attribute in unwanted_attributes:
        if attribute in line:
            return True
    return False

'''Gjør .HODE i fila kompatibel med FKB-arkivet'''
def read_and_modify_head_section(lines):
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

'''Fjerner ..REGISTRERINGSDATO hvis objektet har ..DATAFANGSTDATO'''
def remove_registreringsdato_if_datafangstdato_present(lines):
    processed_lines = []
    current_object = []
    object_has_datafangstdato = False

    for line in lines:
        if line.startswith('.PUNKT') or line.startswith('.KURVE') or (line.strip() == '' and current_object):
            if current_object and object_has_datafangstdato:
                current_object = [obj_line for obj_line in current_object if not obj_line.startswith('..REGISTRERINGSDATO')]
            if current_object:
                processed_lines.extend(current_object)
                if line.strip() == '':  
                    processed_lines.append('\n')
            current_object = []
            object_has_datafangstdato = False
        if '..DATAFANGSTDATO' in line:
            object_has_datafangstdato = True
        if line.strip() != '':  
            current_object.append(line)

    if current_object and object_has_datafangstdato:
        current_object = [obj_line for obj_line in current_object if not obj_line.startswith('..REGISTRERINGSDATO')]
    if current_object:
        processed_lines.extend(current_object)
    return processed_lines

'''Konverterer ..REGISTRERINGSDATO og formaterer datoformat til ..DATAFANGSTDATO hvis objektet ikke allerede har ..DATAFANGSTDATO'''
def convert_and_shorten_registreringsdato(lines):
    processed_lines = []
    current_object = []
    object_started = False 

    for line in lines:
        if line.startswith('.PUNKT') or line.startswith('.KURVE') or (line.strip() == '' and object_started):
            if current_object:
                new_object_lines = []
                for obj_line in current_object:
                    if '..REGISTRERINGSDATO' in obj_line:
                        date = obj_line.split(' ')[1][:8]
                        new_object_lines.append('..DATAFANGSTDATO ' + date + '\n')
                    else:
                        new_object_lines.append(obj_line)
                processed_lines.extend(new_object_lines)
                if line.strip() == '':
                    processed_lines.append('\n')
                current_object = []  
                object_started = False  
        if line.strip() != '': 
            current_object.append(line)
            object_started = True  

    if current_object:
        new_object_lines = []
        for obj_line in current_object:
            if '..REGISTRERINGSDATO' in obj_line:
                date = obj_line.split(' ')[1][:8]
                new_object_lines.append('..DATAFANGSTDATO ' + date + '\n')
            else:
                new_object_lines.append(obj_line)
        processed_lines.extend(new_object_lines)

    return processed_lines


'''Utfører mappingen av egenskaper og fjerner de som ikke er ønsket i FKB'''
def apply_mappings_and_filter(lines, mappings, unwanted_attributes):
    processed_lines = []
    for line in lines:
        if not is_line_unwanted(line, unwanted_attributes):
            line = translate_line(line, mappings)
            processed_lines.append(line)
    return processed_lines

'''Logikk for å sette inn egenskaper fra new_attributes direkte under ..OBJTYPE'''
def insert_new_attributes_under_objects(lines, new_attributes):
    modified_lines = []
    for line in lines:
        modified_lines.append(line)
        if line.strip().startswith('..OBJTYPE'):
            for new_attr in new_attributes:
                if new_attr not in line:
                    modified_lines.append(new_attr + "\n")
    return modified_lines

'''Legger på dummy kvalitetsverdier på objekter som mangler ..KVALITET'''
'''Legger på dummy kvalitetsverdier på objekter som mangler ..KVALITET'''
def missing_kvalitet(lines):
    modified_lines = []  
    current_object_lines = [] 
    kvalitet_present = False  
    processing_object = False  

    for line in lines:
        if line.strip().startswith('.PUNKT') or line.strip().startswith('.KURVE'):
            if processing_object and not kvalitet_present:
                kvalitet_section = [
                    "..KVALITET\n",
                    "...DATAFANGSTMETODE dig\n",
                    "...NØYAKTIGHET 200\n",
                    "...DATAFANGSTMETODEHØYDE gen\n",
                    "...H-NØYAKTIGHET 200\n"
                ]
                objtype_index = next((i for i, line in enumerate(current_object_lines) if '..OBJTYPE' in line), None)
                if objtype_index is not None:
                    current_object_lines[objtype_index+1:objtype_index+1] = kvalitet_section
                kvalitet_present = False

            if current_object_lines:  
                modified_lines.extend(current_object_lines)  
                current_object_lines = []  
            
            processing_object = True  

        if not processing_object:
            modified_lines.append(line)
            continue

        if '..KVALITET' in line:
            kvalitet_present = True

        current_object_lines.append(line)

    if processing_object and not kvalitet_present:
        kvalitet_section = [
            "..KVALITET\n",
            "...DATAFANGSTMETODE dig\n",
            "...NØYAKTIGHET 200\n",
            "...DATAFANGSTMETODEHØYDE gen\n",
            "...H-NØYAKTIGHET 200\n"
        ]
        objtype_index = next((i for i, line in enumerate(current_object_lines) if '..OBJTYPE' in line), None)
        if objtype_index is not None:
            current_object_lines[objtype_index+1:objtype_index+1] = kvalitet_section
        modified_lines.extend(current_object_lines)  

    return modified_lines


'''Mainfunksjonen til scriptet som utfører alle funksjonene og skriver det til en ny fil ved navn NRL_avvik_omkodet.sos'''
def modify_and_process_file(input_file_path, output_file_path, mappings, unwanted_attributes, new_attributes):
    with open(input_file_path, 'r', encoding='utf-8') as input_file:
        lines = input_file.readlines()

    modified_lines = read_and_modify_head_section(lines)
    modified_lines = apply_mappings_and_filter(modified_lines, mappings, unwanted_attributes)
    modified_lines = remove_registreringsdato_if_datafangstdato_present(modified_lines)
    modified_lines = convert_and_shorten_registreringsdato(modified_lines)
    modified_lines = insert_new_attributes_under_objects(modified_lines, new_attributes)
    modified_lines = missing_kvalitet(modified_lines)

    '''Sørger for at fila alltid slutter med linjen .SLUTT'''
    if modified_lines[-1].strip() != ".SLUTT":
        modified_lines = [line.rstrip() for line in modified_lines if line.strip()]
        modified_lines.append(".SLUTT")

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for line in modified_lines:
            output_file.write(line + '\n')  

modify_and_process_file(input_file_path, output_file_path, mappings, unwanted_attributes, new_attributes)
print("Omkodet egenskaper skrevet til:", output_file_path)


