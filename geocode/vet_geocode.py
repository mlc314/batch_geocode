#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 2018
@author: Nathaniel Henry, nathenry@uw.edu

This file contains functions for loading and formatting data for point vetting 
in the geocoding process.

Written in Python 3.6
"""
import numpy as np
import pandas as pd
from geocode.utilities import write_pandas, get_geocoding_suffixes, read_and_prep_input, validate_columns


class VettingData(object):
    """This class handles all data that will be vetted as a """
    def __init__(self, fp, encoding, address_col, iso_col=None):
        self.in_fp = fp
        self.encoding = encoding
        self.address_col = address_col
        self.iso_col = iso_col
        self.raw_data = self.load_data()
        # Create a dictionary template for the geocoding and non-geocoding data
        self.formatted_data = {
            'meta_cols' : None,
            'geo_cols_prevet' : None,
            'geo_cols_postvet' : None
        }
        self.format_in_data()
        self.out_fp = None # To be defined in `save_vetted_data()`
        self.error = None

    def load_data(self):

        in_df, self.encoding, error = read_and_prep_input(self.in_fp, self.encoding)
        '''Load input file as a dataframe'''
        #in_df, self.encoding, error = read_to_pandas(fp=self.in_fp, encoding=self.encoding)

        if(error is not None):
            self.error = error

        invalid_columns = validate_columns(in_df, self.iso_col, self.address_col)
        if(invalid_columns is not None):
            self.error = invalid_columns

        # Create a unique index field
        in_df['__index'] = range( 0, in_df.shape[0] )
        return in_df

    def format_in_data(self):
        '''Split the dataset into "meta" columns that do not contain geocoding
        results and the geocoding results
        '''
        keep_suffixes = get_geocoding_suffixes()
        gc_fields = [c for c in self.raw_data.columns
                       if ( any([c.endswith(s) for s in keep_suffixes]) )
                       or (c==self.address_col)
                       or (self.iso_col is not None and c==self.iso_col)
                       or (c=='__index')]
        meta_fields = [c for c in self.raw_data.columns 
                         if (c not in gc_fields) 
                         or (c=='index')]
        gc_data = self.raw_data.loc[:,gc_fields]
        meta_data = self.raw_data.loc[:,meta_fields]
        # Change the geocoding address and iso columns to standard names
        if self.iso_col is None:
            gc_data['iso2'] = ''
        elif self.iso_col !='iso2':
            gc_data = gc_data.rename({self.iso_col:'iso2'}, axis=1)
        if self.address_col != 'address':
            gc_data = gc_data.rename({self.address_col:'address'}, axis=1)
        # Update the address field so that it includes the index
        gc_data['address'] = gc_data['__index'].apply(str).str.cat(
            gc_data['address'], sep=': '
        )
        gc_data = gc_data.set_index(keys='address')
        # Add to the 'formatted_data' attribute
        self.formatted_data['geo_cols_prevet'] = gc_data.copy()
        self.formatted_data['meta_cols'] = meta_data.copy()

    def get_vetting_data_as_json(self):
        '''Return the input data in JSON format'''
        return self.formatted_data['geo_cols_prevet'].to_json(orient='index')

    def load_vetted_data_json(self, in_json):
        '''Load the vetted JSON data as a data.frame with the same formatting
        as the pre-vetting data'''
        self.formatted_data['geo_cols_postvet'] = pd.read_json(
            in_json,
            orient = 'index',
            encoding = self.encoding
        )

    def save_vetted_data(self, out_fp):
        '''Merge the vetted data back together and save to file'''
        # Make sure that data has been loaded back into this object
        if self.formatted_data['geo_cols_postvet'] is None:
            raise Exception(
                "The vetted data has not been loaded back into this object. "
                "Please load the data and try again.")
            return None
        self.out_fp = out_fp
        # Merge the data together and save
        full_data = pd.merge(
            left = self.formatted_data['meta_cols'],
            right = self.formatted_data['geo_cols_postvet'],
            on = ['__index'],
            how = 'left'
        )
        error = write_pandas(df=full_data, fp=self.out_fp, encoding=self.encoding)
        print(f"Data saved successfully to {self.out_fp}.")

    def get_error(self):
        return self.error
    