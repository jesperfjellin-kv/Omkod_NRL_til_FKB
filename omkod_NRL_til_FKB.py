input_file_path = 'NRL_Avvik.sos'  
output_file_path = 'NRL_Avvik_omkodet.sos'  

mappings = {
    "..OBJTYPE NrlLuftspenn": "..OBJTYPE Trase",
    "..OBJTYPE NrlMast": "..OBJTYPE Mast",
    "..HØYDEREFERANSE": "..HREF",
      
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
    "..LUFTFARTSHINDERLYSSETTING"
   
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


def process_and_write_object_buffer(object_buffer, output_file):
    new_lines = ["..NETTVERKSLEDNINGSTYPE ukjent\n"]
    
    new_object_buffer = []
    
    for line in object_buffer:
        new_object_buffer.append(line)
        
        if line.startswith("..OBJTYPE"):
            new_object_buffer.extend(new_lines)
    
    for line in new_object_buffer:
        if not line.endswith('\n'):
            line += '\n'
        output_file.write(line)
        
def modify_head_section(input_file_path, output_file_path):
    head_section = []
    in_head = False
    sosi_versjon_present = False
    sosi_nivå_present = False
    vert_datum_present = False

    with open(input_file_path, 'r', encoding='utf-8') as infile, open(output_file_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            if '.HODE' in line:
                in_head = True
                head_section.append(line)
                continue
            
            if in_head:
                if '..SOSI-VERSJON' in line:
                    sosi_versjon_present = True
                    if '5.0' not in line:
                        line = '..SOSI-VERSJON 5.0\n'
                elif '..SOSI-NIVÅ' in line:
                    sosi_nivå_present = True
                elif '...VERT-DATUM' in line:
                    vert_datum_present = True
                    if 'NN2000' not in line and not line.strip().endswith('...VERT-DATUM'):
                        continue  # Keep the line as is if it has a different value
                
                head_section.append(line)

                if '..TRANSPAR' in line:
                    if not vert_datum_present:
                        head_section.append('...VERT-DATUM NN2000\n')
                    in_head = False  # End of .HEAD section

            else:
                outfile.write(line)

        if not sosi_versjon_present:
            head_section.insert(1, '..SOSI-VERSJON 5.0\n')
        if not sosi_nivå_present:
            head_section.insert(1, '..SOSI-NIVÅ 3\n')
        head_section.insert(1, '..OBJEKTKATALOG FKBLEDNING 5.0\n')

        # Write the modified head section and the rest of the file
        for line in head_section:
            outfile.write(line)

with open(input_file_path, 'r', encoding='utf-8') as input_file, open(output_file_path, 'w', encoding='utf-8') as output_file:
    object_buffer = []  
    for line in input_file:
        if ".KURVE" in line or ".PUNKT" in line:  
            process_and_write_object_buffer(object_buffer, output_file)
            object_buffer = []  
        
        if not is_line_unwanted(line, unwanted_attributes):
            translated_line = translate_line(line, mappings)
            object_buffer.append(translated_line) 

    process_and_write_object_buffer(object_buffer, output_file)

print("Omkoding har blitt skrevet til:", output_file_path)
