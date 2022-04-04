import sys

mapping = dict()

with open("tipa-to-unicode.tsv","r") as mapping_file:
  for line in mapping_file:
    tipa, unicodeipa = line.strip().split("\t")
    mapping[tipa] = unicodeipa
mapping[" "] = ""
mapping["{}"] = ""
mapping["\\ "] = "\\ "

with open(sys.argv[1],"r") as tex_file:
  line_number = 0
  for line in tex_file:
    line = line.strip()
    line_number += 1
    output_line = ""
    current_tipa = ""
    current_unicodeipa = ""
    current_tipa_char = "" #store characters until found as key in mapping
    current_state = "" #relevant prefix of "\ipa{" consumed so far
    for c in line:
      if current_state == "":
        if c == "\\":
          current_state = "\\"
          current_tipa += c
        else:
          output_line += c
      elif current_state == "\\":
        if c == "i":
          current_state = "\\i"
          current_tipa += c
        else:
          output_line += current_tipa + c
          current_state = ""
          current_tipa = ""
          current_unicodeipa = ""
      elif current_state == "\\i":
        if c == "p":
          current_state = "\\ip"
          current_tipa += c
        else:
          output_line += current_tipa + c
          current_state = ""
          current_tipa = ""
          current_unicodeipa = ""
      elif current_state == "\\ip":
        if c == "a":
          current_state = "\\ipa"
          current_tipa += c
        else:
          output_line += current_tipa + c
          current_state = ""
          current_tipa = ""
          current_unicodeipa = ""
      elif current_state == "\\ipa":
        if c == "{":
          current_state = "tipa"
          current_tipa += c
          current_unicodeipa += "\\UIPA{"
        else:
          output_line += current_tipa + c
          current_state = ""
          current_tipa = ""
          current_unicodeipa = ""
      elif current_state == "tipa":
        current_tipa += c
        if c == "}" and current_tipa_char == "":
          #print(sys.argv[1] + "\t" + str(line_number) + "\t" + current_tipa + "\t" + current_unicodeipa + "}")
          output_line += current_unicodeipa + "}"
          current_tipa = ""
          current_unicodeipa = ""
          current_tipa_char = ""
          current_state = ""
        else:
          current_tipa_char += c
          if current_tipa_char in mapping:
            current_unicodeipa += mapping[current_tipa_char]
            current_tipa_char = ""
          elif len(current_tipa_char) > 25:
            print("ERROR: could not interpret tipa string \"" + current_tipa_char + "\"")
            output_line += current_tipa
            current_tipa = ""
            current_unicodeipa = ""
            current_tipa_char = ""
            current_state = ""
    print(output_line)
