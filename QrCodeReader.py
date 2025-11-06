import cv2
import csv
import sqlite3 as sl
import datetime
import logging

import GSheetsUploader

DB_PATH = "./attendancedb.sqlite3"
CSV_BASE_PATH = "attendance_log.csv"


logger = logging.getLogger(__name__)

class AttendanceRecord:
    def __init__(self, id: int, email: str, name: str, time_in: datetime.datetime):
        self.student_rec_id = id
        self.email = email
        self.name = name
        self.time_in = time_in


def LOG(*logStrs: str):
    logger.info(logStrs)


def getDaysAttendanceRecords(date: datetime.datetime, cur:sl.Cursor) -> list[tuple[int, str, str, int, datetime.datetime]]:
    start = adaptDate(datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0))
    end = adaptDate(datetime.datetime(date.year, date.month, date.day, 23, 59, 59, 999))

    LOG(f"Getting attendance records between {start} and {end}")

    qry = f"""SELECT students.id, students.email, students.name, attendance.student_id, attendance.time_in
             FROM attendance LEFT JOIN students ON attendance.student_id = students.id 
             WHERE attendance.time_in BETWEEN \"{start}\" AND \"{end}\""""
    cur.execute(qry)
    tracked_students = cur.fetchall()
    LOG(f"Got {len(tracked_students)} records")
    return tracked_students

#
def writeCSV(csvPath: str, attendance_records: list[tuple[int, str, str, int, datetime.datetime]]) -> None:
    with open(csvPath, 'w', newline='') as csvfile:
        fieldnames = ['name', 'email', 'time_in']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for student in attendance_records:
            writer.writerow({'name': student[2],
                             'email': student[1],
                             'time_in': student[4]})
            
def uploadCSV(csvPath: str, date: datetime.date) -> None:
    LOG(f"Uploading CSV file: {csvPath}")
    GSheetsUploader.uploadCsvFile(csvPath, date)
            
def processDaysRecords(date: datetime.datetime, cur: sl.Cursor) -> None:
    records = getDaysAttendanceRecords(date, cur)
    csvPath = f"./{date.date().isoformat()}.{CSV_BASE_PATH}"
    if len(records) > 0:
        writeCSV(csvPath, records)
        uploadCSV(csvPath, date.date())
    else:
        LOG(f"No records found for {date.date().isoformat()}. Skipping CSV dump and upload")

# sqlite3 doesn't like default datetime.datetime adapters, so we register ours
def adaptDate(date: datetime.datetime) -> str:
    return date.isoformat()


def convertDate(byteDate: bytes) -> datetime.datetime:
    date = byteDate.decode("utf-8")
    return datetime.datetime.fromisoformat(date)


sl.register_adapter(datetime.datetime, adaptDate)
sl.register_converter("timestamp", convertDate)


def initDB() -> tuple[sl.Connection, sl.Cursor]:
    # Forge connection to db for lifetime of program
    con = sl.connect(DB_PATH,
                     detect_types=sl.PARSE_DECLTYPES | sl.PARSE_COLNAMES)

    # Create cursor in db
    cur = con.cursor()

    # Create new students table if it doesn't exist already
    cur.execute("""CREATE TABLE IF NOT EXISTS students(
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    email VARCHAR(50) NOT NULL,
                    grad_year INTEGER NOT NULL)""")
    
    cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS email_idx ON students(email)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS attendance(
                    id INTEGER PRIMARY KEY,
                    student_id INTEGER,
                    time_in TIMESTAMP,
                    FOREIGN KEY(student_id) REFERENCES students(id))""")

    # Return connection/cursor for later use
    return (con, cur)

def getLatestAttendanceEntry(cur: sl.Cursor, student_email: str):
    cur.execute("""SELECT students.id, students.email, students.name, attendance.student_id, attendance.time_in 
                    FROM students LEFT JOIN attendance ON attendance.student_id = students.id 
                WHERE students.email = ? ORDER BY attendance.time_in DESC LIMIT 1""", (student_email,))
    rec = cur.fetchone()
    if(rec is None): 
        return None
    
    atRec = AttendanceRecord(rec[0] ,rec[1], rec[2], rec[4])
    return atRec

def doesInputMatchRecord(input: str, record: AttendanceRecord) -> bool:
    if record == None:
        return False
    if input != record.email:
        return False
    now = datetime.datetime.now()
    if (record.time_in is None) or (record.time_in.date() != now.date()):
        return False
    
    return True

def addEntry(cur: sl.Cursor, rec: AttendanceRecord) -> None:
    # Grab current date
    date: datetime.datetime = datetime.datetime.now()

    # Insert matched id from QR code alongside date to attendance table
    cur.execute("INSERT INTO attendance (student_id, time_in) VALUES (?, ?)", [rec.student_rec_id, date])

def processInput(input: str, db_cur: sl.Cursor, db_con: sl.Connection) -> AttendanceRecord:
    fetchedRec = getLatestAttendanceEntry(db_cur, input)
    if fetchedRec == None:
        LOG(f"No matching student record for {input}")
        return None
    
    if not doesInputMatchRecord(input, fetchedRec):#No attendance in yet today
        addEntry(db_cur, fetchedRec)
        db_con.commit()

        confirmRec = getLatestAttendanceEntry(db_cur, input)#confirm rec was put properly
        if not doesInputMatchRecord(input, fetchedRec):
            if confirmRec is not None:
                LOG(f"ERROR: failed to correctly input attendance record for {fetchedRec.name}, {fetchedRec.email}")
            else:
                #Should never happen, but lets log just in case
                LOG(f"ERROR: something went wrong updating or fetching from db")
            fetchedRec = None
        else:
            fetchedRec = confirmRec

    return fetchedRec


def signalSuccess(img, data, attendanceRec):
    LOG("Success")
    cv2.putText(img, f"Sign-in Successful",
                (10, 64),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (100, 255, 100), 2)
    cv2.putText(img, f"Welcome {attendanceRec.name}",
                (10, 94),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (100, 255, 100), 2)
    cv2.putText(img, f"({data})",
                (10, 124),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (100, 255, 100), 2)


def signalFailure(img, data):
    LOG("Failed")
    cv2.putText(img, f"Unrecognized ID {data}",
                (10, 64),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 0, 255), 2)
    
def signalError(img, errorMsg: list[str]):
    startOffset = 20 + (35 * (len(errorMsg) - 1))
    for index,msg in enumerate(errorMsg):
        height = img.shape[0] - (startOffset - (index * 35))
        cv2.putText(img, msg,
                    (10, height),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0,0,255), 2)


def main():
    logging.basicConfig(filename="attendanceTracker.log", level=logging.INFO)
    LOG("Starting Up")
    # Initialize the students db with name and students
    db_con, db_cur = initDB()

    # set up camera object called Cap which we will use to find OpenCV
    cap = cv2.VideoCapture(0)

    # QR code detection Method
    detector = cv2.QRCodeDetector()

    cachedAttendanceRec: AttendanceRecord = None
    previousLoopTime = datetime.datetime.now()
    stickyErrorMessage = ["Nightly processing failed","Please inform software leadership"]

    # Infinite loop to constantly search while active
    while True:
        # Below is the method to get a image of the QR code
        _, img = cap.read()

        # Below is the method to read the QR code by detetecting the bounding
        # box coords and decoding the hidden QR data
        try:
            data, bbox, _ = detector.detectAndDecode(img)
        except Exception as exception:
            LOG("IGNORED EXCEPTION:\n", exception)

        # Write the data from the QR code if detected
        # and display the formatted text above it on the gui
        if (bbox is not None):
            if data:
                if not doesInputMatchRecord(data, cachedAttendanceRec):
                    cachedAttendanceRec = processInput(data, db_cur, db_con)
                else:
                    LOG(f"{data} Matches Cached Record, skipping...")

                if cachedAttendanceRec is None:
                    signalFailure(img, data)
                else:
                    signalSuccess(img, data, cachedAttendanceRec)

        if stickyErrorMessage is not None:
            signalError(img, stickyErrorMessage)

        # Below will display the live camera feed to the Desktop
        cv2.namedWindow("code detector", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("code detector",
                              cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow("code detector", img)

        #Dump the previous day when the day changes(midnight)
        currentLoopTime = datetime.datetime.now()
        if currentLoopTime.date() != previousLoopTime.date():
            LOG(f"Processing records for {previousLoopTime.date().isoformat()}")
            try:
                processDaysRecords(previousLoopTime, db_cur)
            except Exception as e:
                logger.error(f"Failed to process records for {previousLoopTime.date().isoformat()}. Exception:{e}")
                stickyErrorMessage = ["Nightly processing failed","Please inform software leadership"]

        previousLoopTime = currentLoopTime

        keyPress = cv2.waitKey(1)
        #press C to clear errors
        if(keyPress == ord("c")):
            stickyErrorMessage = None
        # Press Q to close the app
        if (keyPress == ord("q")):
            break

    # When the code is stopped the below closes all the applications/windows
    cap.release()
    cv2.destroyAllWindows()

    # Close connection to db when done
    db_con.close()

    LOG("Shutting Down...")

if __name__ == "__main__":
    main()
