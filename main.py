# A Project regarding the following Kaggle competition:
# https://www.kaggle.com/c/mercari-price-suggestion-challenge

# Submitted by Yuval Helman and Jakov Zingerman

from mercariPriceData.InferSent.encoder.models import InferSent # change folders
import pandas as pd

import torch
import nltk
import numpy as np

puredata = pd.read_csv('./mercariPriceData/dataset/train.tsv', sep='\t', encoding="utf_8") # change folders


def show_data_structure():
    f = puredata
    print('#################################################')
    print('LOOKING ON THE DATA STRUCTURE:')
    print('#################################################')
    print('data size: ', len(f))
    print(f['name'].unique())

    print("LOOKING ON NUMBER OF UNIQUE VALUES IN EVERY FEATURE:")
    print('item_condition_id: ', len(f['item_condition_id'].unique()))
    print('category_name: ', len(f['category_name'].unique()))
    print('brand_name: ', len(f['brand_name'].unique()))
    print('price: ', len(f['price'].unique()))
    print('shipping: ', len(f['shipping'].unique()))
    print('item_description: ', len(f['item_description'].unique()))
    print('General Info:')
    print(f.info())


    print('value_counts OF THE FEATURES:')
    print(f.item_condition_id.value_counts())
    print(f.shipping.value_counts())
    print(f['brand_name'].value_counts())


    print(f.head())


''' series_to_encode: a 'series' type to be transfered to vectors by infersent '''
''' batch_size_to_encode: number of sentences to encode each time (so we don't run out of RAM) '''
''' return: a dataframe of the sentences encodings to 4096 length vectors'''
# https://github.com/facebookresearch/InferSent
def infersent_encoder(series_to_encode, batch_size_to_encode):
    sentences = series_to_encode.tolist()

    nltk.download('punkt')
    V = 2
    MODEL_PATH = './mercariPriceData/InferSent/encoder/infersent%s.pickle' % V # change folders
    params_model = {'bsize': 64, 'word_emb_dim': 300, 'enc_lstm_dim': 2048,
                    'pool_type': 'max', 'dpout_model': 0.0, 'version': V}
    infersent = InferSent(params_model)
    infersent.load_state_dict(torch.load(MODEL_PATH))
    W2V_PATH = './mercariPriceData/dataset/fastText/cc.en.300.vec' # change folders
    infersent.set_w2v_path(W2V_PATH)
    try:
        infersent.build_vocab(sentences, tokenize=True)
        print("done build vocab")
    except Exception as e:
        print('build vocab failed')
        print(e)

    # Cant Encode all at once.. (not enough RAM) , so we need to do it in batches
    full_embeddings = [list(np.zeros(4096))]
    end_index, start_index, embeddings = 0, 0, 0
    try:
        # Iterate sentences and encode on batches
        start_index = 0
        end_index = start_index + batch_size_to_encode
        #print("blip: ", sentences.count())
        print("number of sentences total: ", len(sentences))
        while (end_index < len(sentences)):
            part_of_sentences = sentences[start_index:end_index].copy() # 0 to 1999
            embeddings = infersent.encode(part_of_sentences, tokenize=True)
            # Iteration phase:
            start_index = end_index
            end_index = start_index + batch_size_to_encode
            full_embeddings = np.append(full_embeddings, embeddings, axis=0)
            # full_embeddings = np.concatenate((full_embeddings, embeddings))

        # when end_index is bigger then the length, do a last encoding
        part_of_sentences = sentences[start_index:end_index].copy()
        embeddings = infersent.encode(part_of_sentences, tokenize=True)
        full_embeddings = np.append(full_embeddings, embeddings, axis=0)

        print("done encoding")
        full_embeddings = full_embeddings[1:]
        full_embeddings = pd.DataFrame.from_records(full_embeddings, #columns=[np.arange(0,4096)]
        )
        return full_embeddings
    except Exception as e:
        print('encoding failed on part of list: ', start_index, end_index)
        print(e)


def data_preprocessing():
    data = puredata.copy()

    # Change anything with Nan \ Not-A-String to an empty string..
    for row_index,val in enumerate(data['item_description']):
        if( isinstance(val , str) == False):
            col_index = data.columns.get_loc("item_description")
            # print(data.iat[row_index, col_index])
            data.iat[row_index, col_index] = ''
            # print("after: ", data.iat[row_index, col_index])
    for row_index,val in enumerate(data['name']):
        if( isinstance(val , str) == False):
            col_index = data.columns.get_loc("name")
            # print(data.iat[row_index, col_index])
            data.iat[row_index, col_index] = ''
            # print("after: ", data.iat[row_index, col_index])
    for row_index, val in enumerate(data['category_name']):
        if (isinstance(val, str) == False):
            col_index = data.columns.get_loc("category_name")
            # print(data.iat[row_index, col_index])
            data.iat[row_index, col_index] = ''
            # print("after: ", data.iat[row_index, col_index])
    for row_index, val in enumerate(data['brand_name']):
        if (isinstance(val, str) == False):
            col_index = data.columns.get_loc("brand_name")
            # print(data.iat[row_index, col_index])
            data.iat[row_index, col_index] = ''
            # print("after: ", data.iat[row_index, col_index])

    # ___________________________________________________________________________________________________
    # Using one-hot encoding on the shipping and item_condition_id columns
    data = pd.concat([data, pd.get_dummies(data['shipping'], prefix='shipping')], axis=1)
    data.drop(columns='shipping', inplace=True)

    data = pd.concat([data, pd.get_dummies(data['item_condition_id'], prefix='item_condition_id')], axis=1)
    data.drop(columns='item_condition_id', inplace=True)
    # ___________________________________________________________________________________________________
    # Using infersent on the item_description column in order to transpose it to vectors (size: 4096)
    data = data.iloc[:100000] # TODO: DEBUG.. erase that for doing for all data
    # print(series_descriptions)
    batch_size_to_encode = 50000

    description_embeddings = infersent_encoder(pd.Series(data["item_description"]), batch_size_to_encode)
    data.drop(['item_description'], axis=1, inplace=True)
    data = pd.concat([data, description_embeddings], axis=1)

    description_embeddings = infersent_encoder(pd.Series(data["name"]), batch_size_to_encode)
    data.drop(['name'], axis=1, inplace=True)
    data = pd.concat([data, description_embeddings], axis=1)

    description_embeddings = infersent_encoder(pd.Series(data["category_name"]), batch_size_to_encode)
    data.drop(['category_name'], axis=1, inplace=True)
    data = pd.concat([data, description_embeddings], axis=1)

    description_embeddings = infersent_encoder(pd.Series(data["brand_name"]), batch_size_to_encode)
    data.drop(['brand_name'], axis=1, inplace=True)
    data = pd.concat([data, description_embeddings], axis=1)
    # ___________________________________________________________________________________________________

    return data


if __name__ == '__main__':
    # TODO: tf-idf
    # TODO: figure out how to change the dataframe and save the changes to a CSV, so we can do the preproccessing only once! :)
    data = data_preprocessing()

    # show_data_structure()
   #print(puredata.head())

    # Save training data into a CSV:
    data.to_csv('./numeric_train.csv', encoding='utf_8', index=False)