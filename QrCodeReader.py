import cv2
import sqlite3 as sl
import datetime

DB_PATH = "./testdb.sqlite3"


# sqlite3 doesn't like default datetime.datetime adapters, so we register ours
def adaptDate(date: datetime.datetime) -> str:
    return date.isoformat()


def convertDate(date: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(date)


sl.register_adapter(datetime.datetime, adaptDate)
sl.register_converter("datetime", convertDate)


def initDB() -> tuple[sl.Connection, sl.Cursor]:
    # Forge connection to db for lifetime of program
    con = sl.connect(DB_PATH,
                     detect_types=sl.PARSE_DECLTYPES | sl.PARSE_COLNAMES)

    # Create cursor in db
    cur = con.cursor()

    # Create new students table if it doesn't exist already
    cur.execute("""CREATE TABLE IF NOT EXISTS students(
                name VARCHAR(20),
                time_in TIMESTAMP)""")

    # Return connection/cursor for later use
    return (con, cur)


def hasExistingEntry(cur: sl.Cursor, data: str) -> bool:
    # Select students matching name
    cur.execute(f"SELECT name FROM students WHERE name='{data}'")

    # Return if any matching students found
    return cur.fetchone() is not None


def addEntry(cur: sl.Cursor, name: str) -> None:
    # Prevent overwriting existing values
    if (hasExistingEntry(cur, name)):
        return

    # Grab current date
    date: datetime.datetime = datetime.datetime.now()

    # Insert name from QR code alongside date to students table
    cur.execute("INSERT INTO students VALUES (?, ?)", [name, date])


def main():
    # Initialize the students db with name and students
    db_con, db_cur = initDB()

    # set up camera object called Cap which we will use to find OpenCV
    cap = cv2.VideoCapture(0)

    # QR code detection Method
    detector = cv2.QRCodeDetector()

    # Infinite loop to constantly search while active
    while True:
        # Below is the method to get a image of the QR code
        _, img = cap.read()

        # Below is the method to read the QR code by detetecting the bounding
        # box coords and decoding the hidden QR data
        try:
            data, bbox, _ = detector.detectAndDecode(img)
        except Exception as exception:
            print("IGNORED EXCEPTION:\n", exception)

        # Write the data from the QR code if detected
        # and display the formatted text above it on the gui
        if (bbox is not None):
            cv2.putText(img, data,
                        (int(bbox[0][0][0]), int(bbox[0][0][1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 250, 120), 2)

            if data:
                addEntry(db_cur, data)
                db_con.commit()

        # Below will display the live camera feed to the Desktop
        cv2.imshow("code detector", img)

        # Press Q to close the app
        if (cv2.waitKey(1) == ord("q")):
            break

    # When the code is stopped the below closes all the applications/windows
    cap.release()
    cv2.destroyAllWindows()

    # Close connection to db when done
    db_con.close()


if __name__ == "__main__":
    main()
