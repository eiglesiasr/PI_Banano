import json
import datetime
import logging.config
import utils as utl

def main():
    try:
    
        # Carga json config
        with open('config.json') as config_file:
            config = json.load(config_file)

        # carga log
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{config['log_dir']}/pi_banano_{current_time}.log"
        

        logging.basicConfig(filename=log_file, level='INFO',
                            format='%(asctime)s - %(levelname)s - %(message)s')


        logging.info('Iniciando Ejecucion Proyecto Integrador Banano')

        logging.info('Lee Credenciales AWS')

        aws_access_key_id=config['aws_access_key_id']
        aws_secret_access_key=config['aws_secret_access_key']
        aws_session_token=config['aws_session_token']

        logging.info('Descargando Datos Zona Raw')
        df = utl.aws_read_s3_raw(aws_access_key_id,
                         aws_secret_access_key,
                         aws_session_token,
                         config['BucketRaw'],
                         config['ArchivoRaw'])


        logging.info('Transformaciones DF')
        df_transformed, columnas_df=utl.df_transformaciones(df)


        logging.info('Descargando Modelo Zona Trusted')
        modeloRegresion=utl.aws_read_model_trusted(aws_access_key_id,
                                                   aws_secret_access_key,
                                                   aws_session_token,
                                                   config['BucketTrusted'],
                                                   config['ModeloRegresion']) 

        logging.info('Realizando Predicciones')

        df_final = utl.df_realiza_predicciones(df_transformed,modeloRegresion)
        
        logging.info('Predicciones Realizadas')


        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.info('Escribiendo Predicciones hacia Zona Trusted')
        utl.aws_write_s3_trusted(aws_access_key_id,
                            aws_secret_access_key,
                            aws_session_token,
                            df_final[columnas_df],
                            config['BucketTrusted'],
                            f'model_predict_{current_time}.xlsx')

        logging.info('Programa Ejecutado Exitosamente')

    except Exception as e:
        # Log the error
        logging.error(f'Error en la ejecucion: {e}', exc_info=True)



if __name__ == "__main__":
    main()