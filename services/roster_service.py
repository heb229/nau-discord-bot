# imports
import pandas as pd

# actual service
class RosterService:
    # initalize object
    def __init__(self, 
                 file_path: str = "data/students.xlsx"):
        
        self.df = pd.read_excel(file_path)

    # function to lookup the student
    def find_student(self, 
                     identifier: str):
        """
        Search by email, username, or userid.
        Returns a dictionary with student data or None.
        """

        # create local ref to dataframe for readability
        df = self.df

        # filter rows where the identifier matches any accepted column
            # user IDs are cast to string to allow numeric or string input
        student_row = df[
            (df["email"] == identifier) |
            (df["username"] == identifier) |
            (df["userid"].astype(str) == str(identifier))
            ]
        
        # if there are no matches, return none
        if student_row.empty:
            return None
        
        # otherwise return the row with the information
        return student_row.iloc[0].to_dict()
