#!/usr/bin/env python
import os
import sys
import argparse
import numpy as np
from skimage import io, exposure, transform, img_as_float
import pydicom
import re


import os

import requests, zipfile
import pandas as pd
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Util methods')
parser.add_argument('-s', metavar='MR_ID_XNAT', type=str, nargs=1,
                    help='display DICOM info for all images of a study identified with MR ID XNAT')
parser.add_argument('-ps', metavar='MR_ID_XNAT', type=str, nargs=1,
                    help='display DICOM info for all images of all studies available for a patient that has a study identified with MR ID XNAT')
parser.add_argument('-p', metavar='PatientID', type=str, nargs=1,
                    help='display DICOM info for all images of all studies available for a patient identified with patientID')

parser.add_argument('-m', metavar='DICOM field modality',
                    help='summarize all values in dataset for the DICOM field modality')
parser.add_argument('-f',  metavar='filename', type=str, nargs='?', default= True,
                    help='save in filename all info for all studies. Default filename: /all_info_studies.csv  ')
parser.add_argument('-d',  metavar='filename', type=str, nargs='?', default= True,
                    help='describe all info for all studies. Default filename: /all_info_studies.csv  ')
parser.add_argument('-dc',  metavar='categorical_field', type=str,
                    help='summarize DICOM field categories for all studies. Default filename: /all_info_studies.csv. Possible categorical fields are '
                         'all,Modality,SeriesDescription,ProtocolName, BodyPartExamined,ViewPosition, CodeMeaning,PhotometricInterpretation, Manufacturer')
parser.add_argument('-dn',  metavar='numerical_field', type=str,
                    help='summarize DICOM numerical field  for all studies. Default filename: /all_info_studies.csv. Possible numerical fields are '
                         'PatientBirth,StudyDate,Rows,Columns,PixelAspectRatio,SpatialResolution, XRayTubeCurrent,ExposureTime, ExposureInuAs,Exposure, RelativeXRayExposure, BitsStored, PixelRepresentation, WindowCenter, WindowWidth')

parser.add_argument('-split',action='store_true',
                    help='split in side and front views based on DICOM info. Default source filename: /all_info_studies.csv.')

parser.add_argument('-e',action='store_true',
                    help='generate list of images to exclude. It excludes non Rx thorax studies or if patient position is not vertical or if image has not associated report. Default source filename: /all_info_studies.csv.')

parser.add_argument('-imgs', metavar='MR_ID_XNAT', type=str, nargs=1,
                    help='preprocess all images of a study identified with MR ID XNAT')

parser.add_argument('-imgm', metavar='n_samples', type=int, nargs=1,
                    help='generate mean X-Ray picture and mean standard deviation picture')

#parser.add_argument('u', metavar='username', type=str, nargs=1,
                    #help='XNAT account username')
#parser.add_argument('p', metavar='password', type=str, nargs=1,
                    #help='XNAT account password')
all_info_studies_file = '/all_info_studies.csv'
args = parser.parse_args()
ID_XNAT = args.s[0] if args.s  else  None
patient_ID_XNAT = args.ps[0] if args.ps  else  None
patient_ID = args.p[0] if args.p  else  None
modality = args.m if args.m  else  None
filename =  all_info_studies_file if args.f is None else None
filename_to_describe =  all_info_studies_file if args.d is None else None
categorical_field = args.dc if args.dc  else  None
numerical_field = args.dn if args.dn  else  None
split_images_side_front = args.split if args.split  else  None
exclude = args.e if args.e  else  None
imgs_ID_XNAT = args.imgs[0] if args.imgs  else  None
sample_image = args.imgm[0] if args.imgm  else  None


#j_username = args.u[0] if args.u  else  ''
#j_password = args.p[0] if args.p  else  ''


currentroot = os.getcwd()
os.chdir("../")
root = os.getcwd()
os.chdir(currentroot)

#get dictionary of image paths and image modality (CT, RX, DX) for a given study identified with ID XNAT
def getImagesPath(ID_XNAT ):
    path = root +  '/SJ/image_dir/'
    fieldValues = {}  # create an empty field dictionary of values
    walk_path = path  if not ID_XNAT else path + ID_XNAT
    for dirName, subdirList, fileList in os.walk(walk_path):
        for filename in fileList:
            if ".dcm" in filename.lower():  # check whether the file's DICOM
                filename = os.path.join(dirName,filename)
                e = np.fromfile(filename, dtype='>u2')
                try:
                    RefDs = pydicom.read_file(filename)

                    value = RefDs.Modality
                    fieldValues[filename] = value

                except:

                    pass

                print(fieldValues)

    print(fieldValues)

    return fieldValues



def getDicomInfo(ID_XNAT):
    path = root + '/SJ'
    walk_path = path + '/image_dir/' + ID_XNAT
    images = {}
    print(str(ID_XNAT))
    for dirName, subdirList, fileList in os.walk(walk_path ):
        for filename in fileList:
            if ".dcm" in filename.lower():  # check whether the file's DICOM
                try:
                    RefDs = pydicom.read_file(os.path.join(dirName,filename),force=True)
                    images['/image_dir_processed/' + ID_XNAT + '_' + filename[-10:-4] + '.png'] = RefDs
                except:
                    print('Failed opening DICOM file')
                    pass
    return images

# Get report + images + Dicom info for a given study identified by ID XNAT
# Precondition: Images need to be previously preprocessed and stored in image_dir
# Arguments: The study identified by MR ID XNAT e.g 171456198269648269029527880939880883235
# Return: the list of image dictionaries that belongs to a study. Each dict contains  patient's and image information fields
def getAllInfo(ID_XNAT, dataset_asoc_DF = None, report_DF = None):
    study_info = {}
    #access number of report
    dataset_asoc = '/dataset_asoc_abril18.csv'
    path = root + '/Rx-thorax-automatic-captioning' + dataset_asoc
    dataset_asoc_DF = pd.read_csv(path, sep = ';', ) if  dataset_asoc_DF is None else dataset_asoc_DF
    exp_id = dataset_asoc_DF.loc[dataset_asoc_DF['MR ID XNAT'] == ID_XNAT]

    study_info['codigoinforme'] = None
    #access report
    try:
        #access number of report
        dataset_asoc = '/dataset_asoc_abril18.csv'
        path = root + '/Rx-thorax-automatic-captioning' + dataset_asoc
        dataset_asoc_DF = pd.read_csv(path, sep = ';', ) if  dataset_asoc_DF is None else dataset_asoc_DF
        exp_id = dataset_asoc_DF.loc[dataset_asoc_DF['MR ID XNAT'] == ID_XNAT]
        exp_id = int(exp_id.iloc[0]['Access Number'])
        study_info['codigoinforme'] = int(str(exp_id)[-7:])
        #access report
        filename = '/report_sentences_preprocessed.csv'
        path = root + '/Rx-thorax-automatic-captioning' + filename
        report_DF = pd.read_csv(path, sep = ',', encoding='ISO-8859-1') if  report_DF is None else report_DF
        text = report_DF.loc[report_DF['codigoinforme'] == study_info['codigoinforme']]

        study_info['report'] = text.iloc[0]['v_preprocessed']
    except:
        study_info['report'] = None
        print("MISSING REPORT: " +str(ID_XNAT) + ' ' + str(study_info['codigoinforme']))
        pass

    print(study_info)

    #access study's images
    images =[]
    dicoms = getDicomInfo(ID_XNAT)
    pattern = re.compile('[\W_]+')
    for key, value in dicoms.items():
        print(value)
        images_info = {}
        images_info["ImagePath"] = key #TODO: image path should be the preprocessed image path not the dcm path
        images_info["StudyID"] = ID_XNAT #A study has 1 to Many images
        images_info["PatientID"] = value.PatientName  if 'PatientName' in value else None #codified patient's name //TODO: use it to ensure that the same patient is not both in the training and testing sets to avoid overfitting
        images_info["PatientBirth"] = str(value.PatientBirthDate)[:4] if 'PatientBirthDate' in value else None
        images_info["PatientSex"] = value.PatientSex if 'PatientSex' in value else None
        images_info['ReportID'] = study_info['codigoinforme']
        images_info['Report'] = study_info['report']
        images_info['StudyDate'] = value.StudyDate if 'StudyDate' in value else None
        images_info['Modality'] = pattern.sub('', value.Modality) if 'Modality' in value else None
        images_info['SeriesDescription'] = pattern.sub('', value.SeriesDescription) if 'SeriesDescription' in value else None
        images_info['ProtocolName'] = pattern.sub('', value.ProtocolName) if 'ProtocolName' in value else None
        images_info['CodeMeaning'] = pattern.sub('', value.ProcedureCodeSequence[0].CodeMeaning) if 'ProcedureCodeSequence' in value and 'CodeMeaning' in value.ProcedureCodeSequence[0] else None
        images_info['Manufacturer'] = pattern.sub('', value.Manufacturer) if 'Manufacturer' in value else None

        images_info['ViewPosition'] = pattern.sub('', value.ViewPosition) if 'ViewPosition' in value else None
        images_info['BodyPartExamined'] = pattern.sub('', value.BodyPartExamined) if 'BodyPartExamined' in value else None #After reviewing this field it is innacurate and inconsistent

        images_info['Rows'] = value.Rows if 'Rows' in value else None
        images_info['Columns'] = value.Columns if 'Columns' in value else None
        images_info['PixelAspectRatio'] = value.PixelAspectRatio if 'PixelAspectRatio' in value else None
        images_info['SpatialResolution'] = value.SpatialResolution if 'SpatialResolution' in value else None
        images_info['PhotometricInterpretation'] = pattern.sub('', value.PhotometricInterpretation)  if 'PhotometricInterpretation' in value else None
        images_info['BitsStored'] = value.BitsStored  if 'BitsStored' in value else None
        images_info['PixelRepresentation'] = value.PixelRepresentation  if 'PixelRepresentation' in value else None
        images_info['WindowCenter'] = value.WindowCenter  if 'WindowCenter' in value else None
        images_info['WindowWidth'] = value.WindowWidth  if 'WindowWidth' in value else None

        images_info['RelativeXRayExposure'] = value.RelativeXRayExposure if 'RelativeXRayExposure' in value else None
        images_info['ExposureTime'] = value.ExposureTime if 'ExposureTime' in value else None #Expressed in sec
        images_info['XRayTubeCurrent'] = value.XRayTubeCurrent if 'XRayTubeCurrent' in value else None
        images_info['ExposureInuAs'] = value.ExposureInuAs if 'ExposureInuAs' in value else None
        images_info['Exposure'] = value.Exposure if 'Exposure' in value else None

        images.append(images_info)

    return images

def saveAllStudyInfoFullDataset(save_file = all_info_studies_file, dataset_asoc_file = '/dataset_asoc_10042018.csv'):
    dataset_asoc = '/dataset_asoc_10042018.csv' if not dataset_asoc_file else dataset_asoc_file
    path = root + '/Rx-thorax-automatic-captioning' + dataset_asoc
    dataset_asoc_DF = pd.read_csv(path, sep = ',', )

    reports = '/report_sentences_preprocessed.csv'
    path = root + '/Rx-thorax-automatic-captioning' + reports
    report_DF = pd.read_csv(path, sep = ',', encoding='ISO-8859-1')


    all_studies_DF = None
    empty = False
    path = root + '/Rx-thorax-automatic-captioning' + save_file
    if os.path.exists(path):
        all_studies_DF = pd.read_csv(path, sep = ';' , header = 0)
    else:
        empty = True
    f = open(path, 'a')


    for index, r in dataset_asoc_DF.iterrows():
        studyID = r['MR ID XNAT']
        if  all_studies_DF is None or not all_studies_DF['StudyID'].str.contains(studyID).any():
            imagesInfo = getAllInfo(studyID,dataset_asoc_DF, report_DF)
            for img in imagesInfo:
                if empty:
                    f.write(";".join(img.keys()) + '\n')
                    empty = False
                f.writelines(";".join(str(e) for e in img.values()) + '\n')

    f.close()

def summarizeAllStudiesDicomModality():
    path = root +  '/SJ/image_dir/'
    fieldValues = {}  # create an empty field dictionary of values
    samples = {}
    for dirName, subdirList, fileList in os.walk(path):
        for filename in fileList:
            if ".dcm" in filename.lower():  # check whether the file's DICOM
                filename = os.path.join(dirName,filename)
                e = np.fromfile(filename, dtype='>u2')
                try:
                    RefDs = pydicom.read_file(filename)

                    value = RefDs.Modality
                    if value in fieldValues.keys():
                        fieldValues[value] +=  1
                    else:
                        fieldValues[value] = 1
                        samples[value] = filename
                except:

                    pass

                print(fieldValues)
                print(samples)
    print(fieldValues)
    print(samples)
    return fieldValues, samples

def splitImagesFrontalSide(file = all_info_studies_file):
    all_studies_DF = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + file, sep = ';' , header = 0)

    #Side view images
    # where StudyDescription is in lat array (a manual selection from values of StudyDescription,
    # please run summarizeAllStudiesByCategory when new images are added to dataset to identify new values)
    lat = ["Lateral","Lateralizq", "LatVertical", "LatHorizontal", "Decblatizq"]
    side_images = all_studies_DF[all_studies_DF['SeriesDescription'].isin(lat)]

    # where ViewPosition is in lat array
    lat = ['LATERAL','LL','LLD','RL'] #LL and RL means right lateral view (all other are left lateral views)
    side_images = side_images.append(all_studies_DF[all_studies_DF['ViewPosition'].isin(lat)])
    side_images = side_images.groupby('ImagePath').first()

    #TODO: add those where image_dir path contain "lat" ? not a good method, is not exhaustive

    #where Code Meaning is in
    lat = ['RXTORAXPAYLAT','RXTORAXPAYLATPED'] #Those are the studies with both frontal and side views, so to not add them but compare with prior figure
    both = all_studies_DF[all_studies_DF['CodeMeaning'].isin(lat)]
    uniqueBoth = both.groupby('ImagePath').first()
    studies_to_review = uniqueBoth[~uniqueBoth['StudyID'].isin(side_images['StudyID'])]
    #side_images = side_images.append(all_studies_DF[all_studies_DF['CodeMeaning'].isin(lat)])
    #side_images = side_images.groupby('ImagePath').first()


    #Front view images where StudyDescription is in front array (a manual selection from values of StudyDescription,
    # please run summarizeAllStudiesByCategory when new images are added to dataset to identify new values)
    front = ["Trax","Tórax","PA", "PAhoriz","APhorizontal","PAvertical", "pulmon", "AP","torax","APhoriz", "APvertical",
    "Lordtica", "APHorizontal", "PAHorizontal","Pediatra3aos", "Pediatría3años","APVertical", "Pedit3aos",  "Pediát3años", "W033TraxPA"]
    front_images = all_studies_DF[all_studies_DF['SeriesDescription'].isin(front)] #Evaluated and Not reliable

    front_images = all_studies_DF[~all_studies_DF['ImagePath'].isin(side_images.index.values)]
    front_images = front_images[~front_images['StudyID'].isin(studies_to_review['StudyID'])]

    side_images.to_csv('position_side_images.csv')
    side_images[side_images['ViewPosition'].isin(['LLD','RL'])].to_csv('position_side_right_images.csv')
    front_images.to_csv('position_front_images.csv')
    studies_to_review.to_csv('position_toreview_images.csv')

    return {'side' : side_images, 'front': front_images }

def summarizeAllStudiesByCategoricalField (file = all_info_studies_file, categorical_field = None):
    #Return dataframe where each row is one class and  values contains the number of ocurrences and one example
    #Possible categorical fields are: 'Modality;SeriesDescription;ProtocolName;ViewPosition;PhotometricInterpretation'
    all_studies_DF = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + file, sep = ';' , header = 0)
    n = all_studies_DF.groupby(categorical_field).first()
    c = all_studies_DF[categorical_field].value_counts()
    n = n.join(c)

    return n
def summarizeAllStudiesByNumericalField (file = all_info_studies_file, numerical_field = None):
    #Return dictionary where each key is one class and each value is a tuple with number of ocurrences and one example
    dict = {}
    all_studies_DF = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + file, sep = ';' , header = 0)
    n = all_studies_DF[numerical_field]
    n = pd.to_numeric(n, errors='coerce')


    return n.describe()
def summarizeAllStudies(file = all_info_studies_file):
    summary = {}
    all_studies_DF = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + file, sep = ';' , header = 0)

    #exclude non-evaluable images
    if os.path.exists('Excluded_images.csv'):
        excluded = pd.read_csv('Excluded_images.csv', sep = ',' , header = 0)
    else:
        excluded = generateExcludedImageList()
    idx = all_studies_DF[all_studies_DF['ImagePath'].isin(excluded['ImagePath'])].index.values
    print("Number of excluded images: " + str(len(idx)))
    all_studies_DF = all_studies_DF.drop(idx)

    #Number of different images
    n = all_studies_DF['ImagePath'].count()
    print("Number of different images: " + str(n))
    #Number of different patients
    np = all_studies_DF.groupby(['PatientID']).count()
    print("Number of different patients: " + str(len(np)))
    print ("Distribution of # of images by patient")
    print ( np['StudyID'].describe())
    #ax = serie.hist()
    #fig = ax.get_figure()
    #fig.savefig('PatientNumberDistribution.pdf')
    #import matplotlib.pyplot as plt
    #s.hist()
    #plt.savefig('path/to/figure.pdf')  # saves the current figure

    #Number of studies per patient (mean, min, max)
    ns = all_studies_DF.groupby(['StudyID']).count()
    print("Number of different studies: " + str(len(ns)))
    #Number of images per study (mean, min, max)
    print("Distribution of # of images per study (mean, min, max): ")
    ns = all_studies_DF.groupby(['StudyID'])['ImagePath'].nunique()
    print(ns.describe())
    ns = all_studies_DF.groupby(['PatientID'])['StudyID'].nunique()
    print("Distribution of # of studies per patient (mean, min, max): ")
    print(ns.describe())
    patients_with_multiple_studies= ns[ns > 1]
    patients_with_multiple_studies.hist()
    plt.title("Histogram of Patients with Multiple Studies (n = " + str(patients_with_multiple_studies.count()) + ")" )
    plt.xlabel("Number of Studies")
    plt.ylabel("Number of Patients")
    plt.savefig('graphs/StudiesPerPatientHistogram.png')
    plt.gcf().clear()
    patients_with_multiple_studies.to_csv('Patients_with_multiple_studies.csv')


    #Birth year (mean, min, max), (distribution by year)
    print ('Birth Year Distribution: ')
    years = all_studies_DF['PatientBirth']
    years = pd.to_numeric(years, errors='coerce')
    print (years.describe())
    years.hist()
    plt.title("Birth Year Histogram (n = " + str(n) + ")" )
    plt.xlabel("Patient's Birth Year")
    plt.ylabel("Images")
    plt.savefig('graphs/BirthYearHistogram.png')  # saves the current figure
    plt.gcf().clear()

    #Age year  (mean, min, max), (distribution by year)
    print ('Age Distribution: ')
    study_dates = all_studies_DF['StudyDate'].apply(lambda x: str(x)[:4])
    ages = pd.to_numeric(study_dates, errors='coerce' ) -  years
    print (ages.describe())
    #ages.hist()
    freq = pd.Series(ages).value_counts().sort_index()
    freq.plot(kind='bar', color='blue', grid=False)
    plt.title("Age Histogram (n = " + str(n) + ")" )
    plt.xlabel("Patient's Age")
    plt.xticks([0,10,20,30,40,50,60,70,80,90,100], [0,10,20,30,40,50,60,70,80,90,100])
    plt.ylabel("Images")
    plt.savefig('graphs/AgeHistogram.png')
    plt.gcf().clear()

    #Sex
    print("Gender Histogram (n = " + str(n) + ")")
    sex = all_studies_DF['PatientSex']
    sex.hist()
    plt.title("Gender Histogram (n = " + str(n) + ")" )
    plt.xlabel("Gender")
    plt.ylabel("Images")
    plt.savefig('graphs/GenderHistogram.png')
    plt.gcf().clear()

    #Sex by age
    print("Age by Gender Histogram (n = " + str(n) + ")")
    ages_sex = all_studies_DF.join(pd.DataFrame({'PatientAge' :ages}))
    ages_sex = ages_sex[ages_sex["PatientSex"].isin(['F','M'])]
    table_ages_sex = pd.crosstab(index=ages_sex["PatientAge"], columns=ages_sex["PatientSex"])
    table_ages_sex.plot(kind='bar', stacked=False, color=['red','blue'], grid=False)

    plt.title("Ages by Gender Histogram (n = " + str(n) + ")" )
    plt.xlabel("Ages")
    plt.xticks([0,10,20,30,40,50,60,70,80,90,100], [0,10,20,30,40,50,60,70,80,90,100])
    plt.ylabel("Images")
    plt.savefig('graphs/AgesByGenderHistogram.png')
    plt.gcf().clear()

    table_ages_sex.plot(kind='box')
    plt.title("Gender Ages Boxplot (n = " + str(n) + ")" )
    plt.xlabel("Gender")
    plt.ylabel("Images")
    plt.savefig('graphs/AgesByGenderBoxplot.png')
    plt.gcf().clear()

    #Study date (distribution by year)
    print('Study Date Distribution')
    study_dates = pd.to_numeric(all_studies_DF['StudyDate'], errors='coerce' ).dropna()
    study_dates = study_dates.apply(lambda x: str(x)[:4] + '-' + str(x)[4:6] + '-' + str(x)[6:8]).astype('datetime64[ns]')
    years = pd.DatetimeIndex(study_dates).year.values
    pd.Series(years).hist()
    plt.title("Study Year Histogram (n = " + str(n) + ")" )
    plt.xlabel("Year of Study")
    plt.ylabel("Images")
    plt.savefig('graphs/StudyYearHistogram.png')
    plt.gcf().clear()


    months = pd.DatetimeIndex(study_dates).month.values
    month_names = ['JAN', 'FEB', 'MAR', 'APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
    freq = pd.Series(months).value_counts().sort_index()
    freq.plot(kind='bar')
    plt.title("Study Month Histogram (n = " + str(n) + ")" )
    plt.xlabel("Month of Study")
    plt.xticks([0,1,2,3,4,5,6,7,8,9,10,11], month_names)
    plt.ylabel("Images")
    plt.savefig('graphs/StudyMonthHistogram.png')
    plt.gcf().clear()


    #Study Type distribution (portatil ['RXSIMPLETORAXPORTATIL1OMASPROYECCIONES','RXTORAXCONPORTATIL'], pediatric ['TORAXPEDIATRICO,'RXTORAXPAYLATPED']
    print("Study Type Histogram (n = " + str(n) + ")")
    type = all_studies_DF['CodeMeaning']
    #type['TypeCat'] = type[type['CodeMeaning'].isin(['RXSIMPLETORAX1OMASPROYECCIONES','RXTORAXLORDOTICAS'])] #Frontal
    #type['TypeCat'] = type[type['CodeMeaning'].isin(['RXSIMPLETORAXPORTATIL1OMASPROYECCIONES','RXTORAXCONPORTATIL'])] #Portatil
    #type['TypeCat'] = type[type['CodeMeaning'].isin(['RXTORAXDLCONRAYOHORIZONTAL'])]#Lateral Izquierda
    type.hist()
    plt.title("Study Type Histogram  (n = " + str(n) + ")" )
    plt.xlabel("Study Type")
    plt.ylabel("Images")
    plt.savefig('graphs/TypeHistogram.png')
    plt.gcf().clear()

    #Radiation exposure levels by study year
    print("Radiation exposure levels by study year")
    temp = pd.DataFrame()
    temp['Year'] = pd.to_numeric(all_studies_DF['StudyDate'], errors='coerce' )
    temp['Exposure'] = pd.to_numeric(all_studies_DF['Exposure'], errors='coerce', downcast='integer' )
    print(temp['Exposure'].describe())
    temp= temp.dropna()
    temp = temp[temp['Exposure'] > 0]
    temp['Year'] = temp['Year'].apply(lambda x: str(x)[:4] + '-' + str(x)[4:6] + '-' + str(x)[6:8]).astype('datetime64[ns]')
    temp['Year'] = pd.DatetimeIndex(temp['Year']).year.values
    pivot = temp.pivot(columns='Year', values='Exposure')
    pivot.boxplot()
    plt.title("Radiation Exposure by Study Year  (n = " + str(n) + ")" )
    plt.xlabel("Years")
    plt.ylabel("Radiation Exposure (mAs)")
    plt.savefig('graphs/RadiationExposureByYear.png')
    plt.gcf().clear()
    pivot.boxplot(showfliers=False)
    plt.title("Radiation Exposure by Study Year  (n = " + str(n) + ")" )
    plt.xlabel("Years")
    plt.ylabel("Radiation Exposure (mAs)")
    plt.savefig('graphs/RadiationExposureByYear_NotOutliers.png')
    plt.gcf().clear()


    #Radiation exposure levels by type of Rx (Lateral vs AP)
    split = splitImagesFrontalSide(all_info_studies_file)
    temp = all_studies_DF['Exposure']
    temp['Position'] = np.where(all_studies_DF['ImagePath'].isin(split['side'].values), 'side', 'unknown')
    #temp['Position'] = np.where(all_studies_DF['ImagePath'].isin(split['front'].values), 'front')




    #Dynamic Range Distribution by type of Rx (Lateral vs AP)


    #generate mean X-Ray picture and mean standard deviation picture



    return summary

def generateMeanXRay(sample = 100):
    #load a sample (n =100 ) of frontal views
    front_studies = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + '/position_front_images.csv',  header = 0)
    front_studies = front_studies.sample(n = 100,random_state=3)
    front_studies = ['9961285849383500700503298594198174646_x4sdaa.png',
                     '99657581807702772616942665484579165452_4yp6fk.png',
                     '99657581807702772616942665484579165452_6exj3e.png',
                     '99676390802057808321172787380479007493_fr7m8g.png',
                     '99689012940057299294497464743812181395_yxad8i.png',
                     '99720463493880780353096930628763941828_c8upl6.png',
                     '99720463493880780353096930628763941828_c8upl8.png',
                     '99741777424569004107876945134365006298_gc3ol0.png',
                     '99744230716892055301280916536204938895_o8z84i.png',
                     '99744230716892055301280916536204938895_oo9nk5.png',
                     '99746950422712167962264033947844105338_2_xdw8ve.png',
                     '99746950422712167962264033947844105338_gzzfd3.png',
                     '99761606121467076641347432617611741801_7ivuix.png',
                     '99761606121467076641347432617611741801_9dy7mx.png',
                     '99828447599555877271076597249310000456_b3fwyn.png',
                     '99828447599555877271076597249310000456_lys6co.png',
                     '99846027070905945425250173033141574241_r1i0ek.png',
                     '99846027070905945425250173033141574241_r1i0em.png',
                     '9985441410843219233283392583438926648_yd9nnr.png',
                     '99856744558733960186100146988515134704_7ah98w.png',
                     '99856744558733960186100146988515134704_j41xjm.png',
                     '99892007883590670741722261257582487413_1oo6g9.png',
                     '99901580345273320160032314107286962521_ku25je.png',
                     '99901580345273320160032314107286962521_mqbbig.png',
                     '99902406960705815671548533715810073618_wu5ixe.png',
                     '99910083627741838065735299152000674832_ma4b5z.png',
                     '99910083627741838065735299152000674832_nqrjxw.png',
                     '99917243543351018409698730282530617147_5cj8jm.png',
                     '99917243543351018409698730282530617147_6f0xsd.png',
                     '9992487839101151026510218029061401063_xwb6x2.png',
                     '9992487839101151026510218029061401063_xwb6x4.png',
                     '99927028802994944546151436477164464059_ihb0dm.png']
    concatenated_img = np.full((400, 400,1), 0) #remove
    #for path in front_studies['ImagePath']:
    for path in front_studies: #change
        #path = '/image_dir_processed/241024778843643004390367414464471495529_me2shq.png'
        path = root + '/SJ/image_dir_processed/' + path #change
        img = img_as_float(io.imread(path))
        img = transform.resize(img, (400,400))
        img = np.expand_dims(img, -1)
        img = np.uint8(img * 255)

        concatenated_img = np.concatenate((concatenated_img,img), axis=2)

    #calculate mean
    mean = np.uint8(np.mean(concatenated_img, axis=2))
    io.imsave('graphs/MeanImage.png',mean)
    std = np.uint8(np.std(concatenated_img, axis=2))
    io.imsave('graphs/StdImage.png',std)

    return


def getAllInfoPatient(patient_ID_XNAT= False , patient_ID=False):
    pd.set_option('display.max_colwidth', -1)
    all_studies_DF = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + all_info_studies_file , sep = ';' , header = 0)
    rows = None
    if patient_ID_XNAT:
        rows = all_studies_DF.loc[all_studies_DF['StudyID'] == patient_ID_XNAT]
        patient_ID = rows.iloc[0]['PatientID']
    studies = all_studies_DF.loc[all_studies_DF['PatientID'] == patient_ID]
    #studies.loc[:,'StudyDate'] =studies.loc[:,'StudyDate'].apply(pd.to_numeric) //FIX ordering not working
    #studies.sort_values(by='StudyDate', ascending=True)
    return studies

def generateExcludedImageList():
    all_studies_DF = pd.read_csv(root + '/Rx-thorax-automatic-captioning' + all_info_studies_file , sep = ';' , header = 0)

    #By Modality: exclude CT or None
    exclude = all_studies_DF[all_studies_DF['Modality'].isin(['None', 'CT'])]
    exclude['ReasonToExclude'] = 'CT'

    #By Series Description: exclude
    series_description = ['Costillasobl812','Costillasobl17','CostillasAP812','CostillasAP17','LatHorizontal','None']
    images = all_studies_DF[all_studies_DF['SeriesDescription'].isin(series_description)]
    images['ReasonToExclude'] = 'SeriesDescription'
    exclude= exclude.append(images)

    #By Protocol Name: exclude
    protocol_name = ['CHEST1VIE','Costillas', 'None','TORAXABDOMENThorax','CHEST1VIECHEST1VIEABDOMEN2VIES']
    images = all_studies_DF[all_studies_DF['ProtocolName'].isin(protocol_name)]
    images['ReasonToExclude'] = 'ProtocolName'
    exclude= exclude.append(images)

    #By Photometric Interpretation: exclude
    photometric_interpretation = ['MONOCHROME1']
    images = all_studies_DF[all_studies_DF['PhotometricInterpretation'].isin(photometric_interpretation)]
    images['ReasonToExclude'] = 'MONOCHROME1'
    exclude= exclude.append(images)

    #Images without reports
    images = all_studies_DF[all_studies_DF['Report'] == 'None']
    images['ReasonToExclude'] = 'NoReport'
    exclude= exclude.append(images)
    nr = '\n'.join(images.groupby('StudyID').groups.keys())
    f = open("Studies_without_reports.csv", 'w')
    f.write(nr)
    f.close()


    exclude.to_csv("Excluded_images_redundant.csv")
    exclude.groupby('ImagePath').first().to_csv("Excluded_images.csv")
    return exclude


def preprocess_images( study_ids = None):
    path = root + '/SJ'

    ConstPixelDims = None
    ConstPixelSpacing = None
    for i, study_id in enumerate(study_ids):
        images = getDicomInfo(study_id)
        for image in images.items():
            RefDs = image[1]
            filename = image[0]
            try:
                # Load dimensions based on the number of rows, columns
                ConstPixelDims = (int(RefDs.Rows), int(RefDs.Columns))
                # Load spacing values (in mm)
                if hasattr(RefDs, 'PixelSpacing'):
                    ConstPixelSpacing = (float(RefDs.PixelSpacing[0]), float(RefDs.PixelSpacing[1]))
                    x = np.arange(0.0, (ConstPixelDims[0]+1)*ConstPixelSpacing[0], ConstPixelSpacing[0])
                    y = np.arange(0.0, (ConstPixelDims[1]+1)*ConstPixelSpacing[1], ConstPixelSpacing[1])
                # The array is sized based on 'ConstPixelDims'
                ArrayDicom = np.zeros(ConstPixelDims, dtype=RefDs.pixel_array.dtype)
                # store the raw image data
                ArrayDicom[:, :] = RefDs.pixel_array
                #img = 1.0 - ArrayDicom * 1. / 4096
                #img = exposure.equalize_hist(img)
                #io.imsave(path + '/image_dir_processed/inverted_' + filename[-10:-4] + '.png', img)
                #Testing
                min = ArrayDicom.min()
                max = ArrayDicom.max()
                print ("ArrayDicom Mean: " + str(ArrayDicom.mean()))
                print ("Window Center: " + str(RefDs.WindowCenter))
                print ("ArrayDicom Min: " + str(min))
                print ("ArrayDicom Max: " + str(max))
                print ("Window Width: " + str(RefDs.WindowWidth))

                cp = np.copy(ArrayDicom)
                nmin = RefDs.WindowCenter - 0.5 - (RefDs.WindowWidth -1)/2
                nmax = RefDs.WindowCenter - 0.5 + (RefDs.WindowWidth -1)/2
                cp[ArrayDicom <= nmin] = min
                cp[ArrayDicom > nmax ] = max
                temp = ((ArrayDicom - (RefDs.WindowCenter - 0.5))/ (RefDs.WindowWidth -1) + 0.5) * (max-min) + min
                cp[ (ArrayDicom <= nmax) & (ArrayDicom > nmin)] = temp[(ArrayDicom <= nmax) & (ArrayDicom > nmin)]


                min = cp.min()
                max = cp.max()
                print ("ProcessedDicom Mean: " + str(cp.mean()))
                print ("ProcessedDicom Min: " + str(min))
                print ("ProcessedDicom Max: " + str(max))

                img =  cp * 1. / 4096
                #img = exposure.equalize_hist(img)
                io.imsave(path + '/image_dir_test/' + study_id + '_' + filename[-10:-4] + '.png', img)
                print ('Lung', i, filename)
            except:
                print ("Unexpected error:", sys.exc_info())




if ID_XNAT is not None:
    getAllInfo(ID_XNAT)


if modality is not None:
    summarizeAllStudiesDicomModality()


if patient_ID_XNAT is not None:
    print(getAllInfoPatient(patient_ID_XNAT =patient_ID_XNAT ))

if patient_ID is not None:
    print(getAllInfoPatient(patient_ID = patient_ID))

if filename is not None:
    saveAllStudyInfoFullDataset(filename)

if filename_to_describe is not None:
    summarizeAllStudies()

if categorical_field is not None:
    if categorical_field == 'all':
        fields = ['Modality','SeriesDescription','ProtocolName', 'BodyPartExamined','ViewPosition', 'CodeMeaning','PhotometricInterpretation', 'Manufacturer']
        for f in fields:
            summarizeAllStudiesByCategoricalField(categorical_field=f).to_csv(f + '.csv')
    else:
        print(summarizeAllStudiesByCategoricalField(categorical_field=categorical_field))

if numerical_field is not None:
    if numerical_field == 'all':
        fields = ['PatientBirth','StudyDate','Rows','Columns','PixelAspectRatio','SpatialResolution', 'XRayTubeCurrent','ExposureTime', 'ExposureInuAs','Exposure', 'RelativeXRayExposure', 'BitsStored', 'PixelRepresentation', 'WindowCenter', 'WindowWidth']
        for f in fields:
            print(summarizeAllStudiesByNumericalField( numerical_field = f))
    else:
        print(summarizeAllStudiesByNumericalField( numerical_field =numerical_field))

if split_images_side_front is not None:
    splitImagesFrontalSide()

if exclude is not None:
    generateExcludedImageList()

if imgs_ID_XNAT is not None:
    if imgs_ID_XNAT == 'test':
        imagePath = ['/image_dir_processed/259099525557219735264115148468152712554_m5ff9v.png',
                  '/image_dir_processed/299164937313584841767678964232362685010_sx5mth.png',
                  '/image_dir_processed/315752159734031831877330441630077004881-2_a83wu8.png']
        study_ids = []
        for image in imagePath:
            study_ids.append( re.search('image_dir_processed/(.+?)_',image).group(1))
        preprocess_images(study_ids)
    else:
        preprocess_images([imgs_ID_XNAT])

if sample_image is not None:
    generateMeanXRay(sample_image)