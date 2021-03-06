# -*- coding: utf-8 -*-
"""SongEncoder.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1AzT0rZlmUu_NC6K8rPb_0IsVGIZkQbrv
"""

import pandas as pd
import keras
import numpy as np

df = pd.read_csv('data.csv', parse_dates=[3])
df.columns = ['Artist', 'Album', 'Song', 'Date']
df.head()

VOCAB_SIZE = 1000

df_g = df.groupby(['Artist', 'Song']).Song.count().rank(method='first', ascending=False).astype(int).sort_values().to_frame()
df_g.columns = ['rank']
#df_g = df_g[df_g['rank']<=VOCAB_SIZE]
df_g = df_g.reset_index()
df_g.head(10)

df = pd.merge(df_g, df, left_on=['Artist', 'Song'], right_on=['Artist', 'Song'])

from collections import Counter

class NegativeSamplingGenerator(keras.utils.Sequence):
  def __init__(self, df, positive_samples, negative_samples, batch_size = 32, window_length=pd.Timedelta(hours=1)):
    self.df = df
    self.positive_samples = positive_samples
    self.negative_samples = negative_samples
    self.window_length = window_length
    self.batch_size = batch_size
    self.app_counter = Counter()
    
  def __len__(self): #Batches per epoch == Words to generate per epoch
    return self.batch_size
  
  def __getitem__(self, index):
    fixed_element = self.df.sample(1).iloc[0]
    self.app_counter[fixed_element['Artist'] + ' - ' + fixed_element['Song']]+=1
    positive = self.df[(self.df.Date >= fixed_element.Date - self.window_length) & \
                       (self.df.Date <= fixed_element.Date + self.window_length)] \
                .sample(self.positive_samples, replace=True)['rank'].values
    negative = self.df.sample(self.negative_samples)['rank'].values
    """
    X = np.zeros((self.positive_samples + self.negative_samples, 2))
    X[:,0] = fixed_element['rank']
    X[:,1] = np.concatenate((positive, negative))
    """
    X1 = np.full((self.positive_samples + self.negative_samples,), fixed_element['rank'])
    X2 = np.concatenate((positive, negative))
    Y = np.array([1]*self.positive_samples + [0]*self.negative_samples)
    #print([X1, X2], Y)
    return [X1, X2], Y

# Adapted from https://github.com/adventuresinML/adventures-in-ml-code/blob/master/keras_word2vec.py

from keras.layers import Input, Dense, Reshape, Dot
from keras.layers.embeddings import Embedding
from keras.models import Model


# vocab_size = # of different sogns
# vector_dim = embedding dimensions
def create_model(vocab_size, vector_dim):
  input_target = Input((1,))
  input_context = Input((1,))

  embedding = Embedding(vocab_size, vector_dim, input_length=1, name='embedding')
  target = embedding(input_target)
  target = Reshape((vector_dim, 1))(target)
  context = embedding(input_context)
  context = Reshape((vector_dim, 1))(context)

  dot_product = Dot(axes=1)([target, context])
  dot_product = Reshape((1,))(dot_product)
  output = Dense(1, activation='sigmoid')(dot_product)
  
  model = Model(inputs=[input_target, input_context], outputs=output)
  return model

VECTOR_DIM = 20
model = create_model(VOCAB_SIZE, VECTOR_DIM)

model.summary()

model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
data_generator = NegativeSamplingGenerator(df, 1, 10, batch_size=256, window_length=pd.Timedelta(days=2))

model.fit_generator(data_generator, epochs=5000, verbose=1)

song_to_vec = {}

embedding_matrix = model.get_layer('embedding').get_weights()[0]

for i, row in df_g.iterrows():
  song_name = row.Artist + ' - ' + row.Song
  song_to_vec[song_name] = embedding_matrix[i]

def cosine_similarity(a, b):
  return np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b))

def song_similarity(songA, songB):
  return cosine_similarity(song_to_vec[songA], song_to_vec[songB])

def find_most_similar(song, k):
  song_vec = song_to_vec[song]
  ans = sorted(list(song_to_vec.items()), key=lambda x : cosine_similarity(song_vec, x[1]), reverse=True)[:k]
  return [(song, cosine_similarity(song_vec, vec)) for song, vec in ans]

song_similarity('Maroon 5 - Maps', 'Bayside - Montauk')

find_most_similar("Maroon 5 - Maps", 10)

from collections import Counter

title_searched = 'Morandi - Summer in December'
artist_searched, song_searched = title_searched.split(' - ')
df_apps = df[(df.Song==song_searched) & (df.Artist==artist_searched)]
related = Counter()
for i, row in df_apps.iterrows():
  df_related = df[(df.Date >= row['Date'] - pd.Timedelta(days=2)) & (df.Date <= row['Date'] + pd.Timedelta(days=2))]
  for j, row2 in df_related.iterrows():
    related[row2['Artist'] + ' - ' + row2['Song']] += 1
related.most_common(20)

all_songs = (df.Artist + ' - ' + df.Song).values
all_songs

from gensim.models import Word2Vec

word2vec = Word2Vec([all_songs.tolist()], size=5, window=10, min_count=20, iter=100)

word2vec.wv.most_similar(['Morandi - Summer in December'])