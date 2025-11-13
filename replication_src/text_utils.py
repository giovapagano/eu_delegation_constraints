# replication_src/text_utils.py

import re


# --- FORMULAS & WORD LISTS ---
start_formulas = [
    "HAS ADOPTED THIS REGULATION",
    "HAS ADOPTED THIS DIRECTIVE",
    "HAS ADOPTED THE FOLLOWING REGULATION",
    "HAS ADOPTED THE FOLLOWING DIRECTIVE",
    "HAVE ADOPTED THIS REGULATION",
    "HAVE ADOPTED THIS DIRECTIVE",
    "HAVE ADOPTED THE FOLLOWING REGULATION",
    "HAVE ADOPTED THE FOLLOWING DIRECTIVE"
    ]

stop_formulas = [
    "Done at Luxembourg",
    "DONE AT LUXEMBOURG",
    "Done at Brussels",
    "DONE AT BRUSSELS",
    "Done at Paris",
    "DONE AT PARIS",
    "Done at Strasbourg",
    "DONE AT STRASBOURG"
    ]


# List of words that should be uppercased
uppercase_words = ['JAA', 'COCOLAF', 'ACER', 'BEREC', 'CESR', 'CEBS', 'CEIOPS', 'COG', 'TRAN', 'CSWP', 'EFC', 'IMPEL NETWORK', 'EAR', 'EU-OSHA', 'EMEA', 'FRONTEX', 'OLAF', 'EASO', 'EASA', 'EBA', 'ECB', 'ECHA', 'ECN', 'ECC-NET', 'EDPS', 'EDA', 'EIONET', 'EEA', 'EEAS', 'EFCA', 'EFSA', 'GSA', 'REITOX', 'EIOPA', 'EIB', 'ELA', 'EMSA', 'EMA', 'EMI', 'EMCDDA', 'EUMC', 'ENCA', 'ENPE', 'EUROSAI', 'EPPO', 'ERA', 'ERGP', 'ESMA', 'ESA', 'ESCB', 'EUROJUST', 'ENISA', 'EUROPOL', 'CEPOL', 'EU-LISA', 'EUISS', 'EUMC', 'SATCEN', 'FRAN', 'FRA', 'EEJ-NET', 'EPA', 'COPS', 'PSN', 'ECDPC']

# List of words that should be capitalized
capitalize_words = ['central bank', 'kingdom of belgium', 'republic of bulgaria', 'czech republic', 'kingdom of denmark', 'federal republic of germany', 'republic of estonia', 'ireland', 'hellenic republic', 'kingdom of spain', 'french republic', 'republic of croatia', 'italian republic', 'republic of cyprus', 'republic of latvia', 'republic of lithuania', 'grand duchy of luxembourg', 'republic of hungary', 'republic of malta', 'kingdom of the netherlands', 'republic of austria', 'republic of poland', 'portuguese republic', 'romania', 'republic of slovenia', 'slovak republic', 'republic of finland', 'kingdom of sweden', 'united kingdom', 'benelux countries', 'luxembourg', 'france', 'netherlands', 'belgium', 'bulgaria', 'czechia', 'denmark', 'germany', 'estonia', 'ireland', 'greece', 'spain', 'france', 'croatia', 'italy', 'cyprus', 'latvia', 'lithuania', 'luxembourg', 'hungary', 'malta', 'netherlands', 'austria', 'poland', 'portugal', 'romania', 'slovenia', 'slovakia', 'finland', 'sweden', 'united kingdom', 'the commission', 'european commission', 'advisory committee for the coordination of fraud prevention', 'agency for the cooperation of energy regulators', 'body of european regulators for electronic communications', 'committee', 'committee of european securitiesregulators', 'committee of european banking supervisors', 'committee of european insurance and occupationalpension\'s supervisors', 'committee of governors', 'committee on transports', 'data protection working party', 'economic and financial committee', 'european network for the implementation and enforcement of environmental law', 'eu network of independent experts on fundamental rights', 'european agency for reconstruction', 'european agency for safety and health at work', 'european agency for the evaluation ofmedicinal products', 'european agency for the management of operational cooperation at the external borders', 'european anti-fraud office', 'european asylum support office', 'european aviation safety authority', 'european banking authority', 'european border and coast guard agency', 'european central bank', 'european chemical agency', 'european competition network', 'european conference of privacy commissioners', 'european consumer centresnetwork', 'european crime prevention network', 'european data protection supervisor', 'european defence agency', 'european environment information and observation network', 'european environmental agency', 'european external action service', 'european fisheries control agency', 'european food safety authority', 'european foodsafety network', 'european gas regulatory forum', 'european global navigation satellite systems agency', 'european heads of medicines agency regulatory network', 'european information network on drugs and drug addiction', 'european insurance and occupational pensions authority', 'european investment bank', 'european judicial network', 'european labour authority', 'european maritime safety agency', 'european medicines agency', 'european medicines evaluation agency', 'european monetary institute', 'european monitoring centre for drugs and drugaddiction', 'european monitoring centre on racism and xenophobia', 'european network of prosecutors for the environment', 'european platform of regulatory authorities', 'european public prosecutor office', 'european railway agency', 'european regulators group for electronic communications networks and services', 'european regulators groups for electricity and gas', 'european regulatory group', 'european regulatory group for postal services', 'european securities and markets authority', 'european space agency', 'european system of central banks', 'europeanunion agency for criminal justice cooperation', 'european network and information security agency', 'europeanunion agency for cybersecurity', 'european union agency for law enforcement cooperation', 'european unionagency for law enforcement training', 'european union agency for the operational management of large-scale itsystems in the area of freedom', 'european union institute for security studies', 'european union militarycommittee', 'european union satellite centre', 'expert forum on rights', 'florence forum for electricity', 'frontex risk analysis network', 'european union agency for fundamental rights', 'independent regulators group', 'joint nuclear research centre', 'joint supervisory authority', 'madrid forum for gas', 'monetary committee', 'national contactpoints', 'network for the extra-judicial settlement of consumer disputes', 'network of the heads of environment protection agencies', 'olaf anti-fraud communicators network', 'permanent working party on drugs', 'political and security committee', 'product safety network', 'social protection committee', 'working party on rail transport', 'working party on the protection of individuals with regard to the processing of personal data', 'european centre for disease prevention and control']


# Removes sentences that start with "whereas" or "having regard" to eliminate introductory or background information that is not central to the legal content.

def filter_sentence(sentence):
    if not (sentence.lower().startswith('whereas') or sentence.lower().startswith('having regard')):
        return sentence
    return None


# Splits text based on specific patterns and modal verbs, to break down texts into lists of sentences.

def split_lists(text):
  pattern = r'(?<=[;:])\s*(?: and| or)?\s*\((?![ivxIVX]+)\s*([a-hj-zA-HJ-Z])\s*\)'
  modal_pattern = r'\b(can|could|may|might|must|will|would|should|shall)\b'

  # Check for the modal verb pattern followed by a colon
  if re.search(modal_pattern + r':', text):
      matches = re.findall(pattern, text)
      prefix = text.split(':')[0].strip()

      sentences = re.split(pattern, text)

      new_sentences = []
      for i in range(len(sentences) // 2):
          index = 2 * i
          new_sentence = prefix + sentences[index + 2]
          new_sentences.append(new_sentence)

      return new_sentences
  else:
      return text

# Handling uppercase text

## The following functions are used to convert mostly uppercase text to proper case and ensures specific words remain uppercase or are capitalized as needed.


def is_mostly_uppercase(sentence):
    if not sentence.strip():
        return False

    uppercase_count = sum(1 for char in sentence if char.isupper())
    total_chars = len(sentence.replace(' ', ''))
    percentage_uppercase = (uppercase_count / total_chars) * 100

    return percentage_uppercase >= 90

def lowercase_text(sentence):
    # Split the text into words
    words = sentence.split()

    # Process each word
    for i in range(len(words)):
        # Check if the word should remain in uppercase
        if words[i].upper() in uppercase_words:
            words[i] = words[i].upper()
        else:
            # Check if the word should be capitalized
            if words[i].lower() in capitalize_words:
                words[i] = words[i].capitalize()
            else:
                words[i] = words[i].lower()

    # Ensure the first word of the sentence is capitalized
    if len(words) > 0:
        words[0] = words[0].capitalize()

    # Reconstruct the modified text
    modified_text = " ".join(words)
    return modified_text


    import re



# Removes elements like article references or numbers that appear at the beginning of sentences, which might be redundant.

def remove_elements_beginning(sentence):
    patterns = [
        r'\bArticle\s+\w+\b',  # Pattern to remove 'Article' followed by a word at the beginning of a sentence
        r'^\(\s*[a-zA-Z0-9]+\s*\)',  # Pattern to remove a letter between round brackets at the beginning of a sentence
        r'^(?:\d+\.\s?)'  # Pattern to identify a number followed by a dot at the beginning of a sentence
    ]

    # Check each pattern against the sentence
    for pattern in patterns:
        if re.match(pattern, sentence):
            # If a match is found, remove the pattern
            processed_sentence = re.sub(pattern, '', sentence)
            return processed_sentence.strip()

    # If no match is found, return the original sentence
    return sentence



# The following divides sentences into meaningful chunks based on conjunctions, allowing to analyze each segment individually.

def segment_sentence_into_chunks(text, nlp):
  newdoc = nlp(text)
  for sentence in newdoc.sents:
      seen_words = set()
      sentence_root = sentence.root
      conjunction_heads = [child for child in sentence_root.children if (child.dep_ == 'conj'
                                                                        and (child.pos_ == 'AUX' or child.pos_ == 'VERB'))]
      sentence_chunks = []

      for conjunction_head in conjunction_heads:
          words_in_chunk = [word for word in conjunction_head.subtree]
          for word in words_in_chunk:
              seen_words.add(word)

          chunk_text = ' '.join([word.text for word in words_in_chunk])
          sentence_chunks.append(chunk_text)

      unseen_words = [word for word in sentence if word not in seen_words]
      unseen_chunk_text = ' '.join([word.text for word in unseen_words])
      sentence_chunks.append(unseen_chunk_text)
      sentence_chunks.reverse()  # Reversing the order of chunks

  #    print(sentence_chunks)

      return sentence_chunks


# semicolon splitting

def semicolon_splitting(text):
    # Split the text into sentences using semicolons as separators
    chunks = text.split(';')

    # Process each sentence
    processed_sentences = []
    for chunk in chunks:
        # Find the first word and capitalize it
        words = chunk.strip().split(' ')
        if words:
            words[0] = words[0].capitalize()
            capitalized_sentence = ' '.join(words)
            processed_sentences.append(capitalized_sentence)

    return processed_sentences


