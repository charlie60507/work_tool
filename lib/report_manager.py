
ON_GOING_STATUS = {"Open", "In Progress", "Code Review", "Reopened"}
COMPLETED_STATUS = {"Ready for QA", "Closed"}

def get_weekly_report(records):
    on_going_records = []
    completed_records = []

    # add to categories
    for record in records:
        status = record["status"].split(". ")[-1]
        formatted_record = f"- <{record['jiraUrl']}|{record['jiraId']}> {record['title']} `{status}`"
        if status in ON_GOING_STATUS:
            on_going_records.append(formatted_record)
        elif status in COMPLETED_STATUS:
            completed_records.append(formatted_record)
        
    # generate report
    result = []
    
    result = []
    if on_going_records:
        result.append("On Going:")
        result.extend(on_going_records)
    if completed_records:
        result.append("\nCompleted:")
        result.extend(completed_records)
    result.append("\nSummary:")

    return "\n".join(result)
