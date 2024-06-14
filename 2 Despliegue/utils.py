import logging
import boto3
import pandas as pd
import unidecode
import pickle
from pandasql import sqldf
from io import BytesIO
import statsmodels.api as sm



datatypes={'Ano': 'int64',
 'Semana': 'int64',
 'Zona': 'category',
 'Finca': 'category',
 'municipio': 'category',
 'temp_media': 'float64',
 'Precipitacion': 'float64',
 'Humedad_relativa': 'float64',
 'Velocidad_del_viento': 'float64'}

def generarSQLRezago(colname,n_rezagos):
    sql=''
    for i in range(1,n_rezagos+1):
        semana=n_rezagos-i
        sql=sql+f'''lag({colname},{i},null) over (partition by zona,finca,municipio order by ano*100+semana asc) {colname}_lag{i},\n'''
    return sql[0:len(sql)-2]

def aws_read_s3_raw(aws_access_key_id,aws_secret_access_key,aws_session_token,bucket_name,filename):
    # Do something with the parameters
    logging.info(f'Descargando archivo: {filename} desde S3 Zona Raw')

    
    session = boto3.Session(aws_access_key_id,aws_secret_access_key,aws_session_token)
    s3=session.client('s3')
    
    response = s3.get_object(Bucket=bucket_name, Key=filename)
    excel_data = response['Body'].read()

    excel_data_io = BytesIO(excel_data)

    
    df = pd.read_excel(excel_data_io)

    return df


def df_transformaciones(df):


    logging.info(f'Arreglando Nombre Columnas')

    columns=df.columns
    columns =[unidecode.unidecode(c).replace(' ','_').replace('(','').replace(')','') for c in columns]
    df.columns=columns

    logging.info(f'Modificando tipos de datos')

    for col,dtype in datatypes.items():
        df[col]=df[col].astype(dtype)

    logging.info(f'Agregando Variables Dummies')

    df['Centro']=df['Zona'].apply(lambda x: 1 if x=='CENTRO' else 0)
    df['Sur']=df['Zona'].apply(lambda x: 1 if x=='SUR' else 0)

    logging.info(f'Agregando Rezagos')

    n_resagos=51
    df_rezagos=sqldf(f'''select ano, 
                    semana,
                    zona,
                    finca,
                    municipio,
                    centro,
                    sur,
                    temp_media,
                    Precipitacion,
                    Humedad_relativa,
                    Velocidad_del_viento,
                    {generarSQLRezago('temp_media',n_resagos)},
                    {generarSQLRezago('Precipitacion',n_resagos)},
                    {generarSQLRezago('Humedad_relativa',n_resagos)},
                    {generarSQLRezago('Velocidad_del_viento',n_resagos)}
    from df ''')

    df_rezagos=df_rezagos.fillna(0)

    columnas_para_retornar=['Ano','Semana','Zona','Finca','municipio','temp_media','Precipitacion','Humedad_relativa','Velocidad_del_viento','Peso_total_del_racimo_kg_predict']

    return df_rezagos, columnas_para_retornar


def aws_write_s3_trusted(aws_access_key_id,aws_secret_access_key,aws_session_token,df,bucket_name,filename):
    logging.info(f'Cargando archivo: {filename} hacia S3 Zona Trusted')

    
    session = boto3.Session(aws_access_key_id,aws_secret_access_key,aws_session_token)
    s3=session.client('s3')

    with BytesIO() as output:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        data = output.getvalue()

    s3.put_object(Bucket=bucket_name, Key=filename, Body=data)


def aws_read_model_trusted(aws_access_key_id,aws_secret_access_key,aws_session_token,bucket_name,modelname):
    logging.info(f'Descargando PKL Modelo: {modelname} desde S3 Zona Trusted')

    
    session = boto3.Session(aws_access_key_id,aws_secret_access_key,aws_session_token)
    s3=session.client('s3')

    try:
        obj = BytesIO()  
        s3.download_fileobj(bucket_name, modelname, obj)
        obj.seek(0)

        logging.info(f'Descarga Exitosa')
        
        modelo=pickle.load(obj)

        return modelo
    except Exception as e:
        logging.error(f'Error al descargar PKL Modelo: {e}', exc_info=True)


def df_realiza_predicciones(df,modeloRegresion):
    _, variables_predictoras, modelo, _, _, _, _ = modeloRegresion.iloc[0]

    df['Peso_total_del_racimo_kg_predict']=modelo.predict(df[variables_predictoras])
    
    return df


