import numpy as np
import pandas as pd


class TEDA:
    """Class used to detect outliers on the data"""
    # ------------------------------
    # CONSTRUCTOR
    #-------------------------------
    def __init__(self):
        # initialize variables
        self.k = 1
        self.variance = 0
        self.mean = 0

    # ------------------------------
    # INTERNAL METHODS
    #------------------------------- 
    def __calcMean(self, x):
        return ((self.k-1)/self.k)*self.mean + (1/self.k)*x
    
    def __calcVariance(self, x):
        distance_squared = np.square(np.linalg.norm(x - self.mean))
        return ((self.k-1)/self.k)*self.variance + distance_squared*(1/(self.k - 1))
                                     
    def __calcEccentricity(self, x):
        return (1 / self.k) +  (((self.mean - x).T.dot((self.mean - x))) / (self.k *  self.variance))
    
    # ------------------------------
    # RUN METHODS
    #-------------------------------
    def run_offline(self, df, features):
        """Run the algorithm offline"""
        
        # calculate n from the length of the feature list
        #n = len(features)
        n=2.5
        # add is_outlier column to the dataframe
        df['is_outlier'] = False
        
        print('Features: ', features)
        print('Dimensions: ', n)
        
        # loop through the rows in df
        for index, row in df.iterrows():
            # build the X sample numpy array
            x = np.array(row[features])
            
            # update the model metrics
            if(self.k == 1):
                self.mean = x
                self.variance = 0
            else:
                # calculte the new mean
                self.mean = self.__calcMean(x)
                # calculate the new variance
                self.variance = self.__calcVariance(x)
                # calculate the eccentricity and nomalized eccentricity
                eccentricity = self.__calcEccentricity(x)
                norm_eccentricity = eccentricity/2
                # define the threshold for outlier detection
                threshold = (n**2 +1)/(2*self.k)
                
                # check if the point is an outlier
                isOutlier = norm_eccentricity > threshold

                # if the point is an outlier, add it to the outlier list
                if (isOutlier):
                    df.at[index, 'is_outlier'] = True

            # Update the timestamp
            self.k = self.k + 1
            
        print('Outlier value counts')
        print(df.is_outlier.value_counts())

    def run(self, features):
        "Run the algorithm online"""
    
        # calculate n from the length of the feature list
        n = len(features)

        # build the X sample numpy array
        x = np.array(features)

        is_outlier = False
        
        # update the model metrics
        if(self.k == 1):
            self.mean = x
            self.variance = 0
        else:
            # calculte the new mean
            self.mean = self.__calcMean(x)
            # calculate the new variance
            self.variance = self.__calcVariance(x)
            # calculate the eccentricity and nomalized eccentricity
            eccentricity = self.__calcEccentricity(x)
            norm_eccentricity = eccentricity/2
            # define the threshold for outlier detection
            threshold = (n**2 +1)/(2*self.k)
            
            # check if the point is an outlier
            isOutlier = norm_eccentricity > threshold

            # if the point is an outlier, add it to the outlier list
            if (isOutlier):
                is_outlier = True

        # Update the timestamp
        self.k = self.k + 1

        return is_outlier