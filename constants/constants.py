# Status messages

# Status message, inserted
STATUS_INSERTED = "inserted"

# Status message, report updated
STATUS_REPORT_UPDATED = "Report status updated to "

# Status message, enter a number
STATUS_ENTER_NUMBER = "Please enter a number."

# Status message, no entry for sentence id
STATUS_NO_ENTRY_SENTENCE_ID = "There is no entry for sentence id "

# Status message, successfully moved sentence       
STATUS_SENTENCE_MOVED = "Successfully moved sentence "


# Database table names

# Database table attack
DB_TABLE_ATTACK = "attack_uids"

# Database table true_positives
DB_TABLE_TRUE_POSITIVES = "true_positives"

# Database table false_positives
DB_TABLE_FALSE_POSITIVES = "false_positives"

# Database table true_negatives
DB_TABLE_TRUE_NEGATIVES = "true_negatives"

# Database table false_negatives
DB_TABLE_FALSE_NEGATIVES = "false_negatives"

# Database table reports
DB_TABLE_REPORTS = "reports"

# Database table report_sentences
DB_TABLE_REPORT_SENTENCES = "report_sentences"

# Database table report_sentence_hits
DB_TABLE_REPORT_SENTENCE_HITS = "report_sentence_hits"

# Database table regex_patterns
DB_TABLE_REGEX_PATTERNS = "regex_patterns"

# Database table original_html
DB_TABLE_ORIGINAL_HTML = "original_html"

# Database table similar_words
DB_TABLE_SIMILAR_WORDS = "similar_words"

# Database queries

# The SQL select join query to retrieve the confirmed techniques for the report from the database
SQL_SELECT_JOIN_CONFIRMED_TECHNIQUES = (
    "SELECT report_sentences.uid, report_sentence_hits.attack_uid, report_sentence_hits.report_uid, report_sentence_hits.attack_tid, true_positives.true_positive " 
    "FROM ((report_sentences INNER JOIN report_sentence_hits ON report_sentences.uid = report_sentence_hits.uid) " 
    "INNER JOIN true_positives ON report_sentence_hits.uid = true_positives.sentence_id AND report_sentence_hits.attack_uid = true_positives.uid) " 
    "WHERE report_sentence_hits.report_uid = {} "
    "UNION "
    "SELECT report_sentences.uid, report_sentence_hits.attack_uid, report_sentence_hits.report_uid, report_sentence_hits.attack_tid, false_negatives.false_negative " 
    "FROM ((report_sentences INNER JOIN report_sentence_hits ON report_sentences.uid = report_sentence_hits.uid) " 
    "INNER JOIN false_negatives ON report_sentence_hits.uid = false_negatives.sentence_id AND report_sentence_hits.attack_uid = false_negatives.uid) " 
    "WHERE report_sentence_hits.report_uid = {}")