import pandas as pd
import streamlit as st
import seaborn as sns
import locale
import matplotlib.pyplot as plt

from scipy import stats
from matplotlib.ticker import MaxNLocator

def get_data(path):
    df = pd.read_csv('datasets/kc_house_data.csv')

    return df

def treat_data(df):
    # formata valores monetários
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    # converte tipos de dados
    df['date'] = pd.to_datetime(df['date'])
    df['bathrooms'] = df['bathrooms'].astype(int)
    df['floors'] = df['floors'].astype(int)
    df['waterfront'] = df['waterfront'].apply(lambda x: 'yes' if x == 1 else 'no')
    df['m2_basement'] = df['sqft_basement']*0.3048
    df['m2_living'] =  df['sqft_living']*0.3048
    df['m2_lot'] = df['sqft_lot']*0.3048
    df['lon'] = df['long']

    # Create a column that tells whether the house has a basement
    df.loc[df['m2_basement'] == 0, 'has_basement'] = 'no'
    df.loc[df['m2_basement'] > 0, 'has_basement'] = 'yes'

    # cria uma coluna com a média do preço da região de cada casa
    df['price_mean_by_zipcode'] = df[['price', 'zipcode']].groupby('zipcode').transform('mean')

    df['condition_type'] = df['condition'].apply(
        lambda x:
        'bad' if x <= 2
        else 'regular' if (x == 3) | (x == 4)
        else 'good' if x == 5
        else 'NA'
    )

    # Inverno de dezembro a fevereiro
    # Primavera de maro a maio
    # Verão de junho a agosto
    # Outono de setembro a novembro

    # cria uma coluna com a sazonalidade da data para a venda de cada casa
    df['season'] = df['date'].dt.month.apply(
        lambda x:
        'winter' if (x == 12) | (x <= 2)
        else 'spring' if (x >= 3) & (x <= 5)
        else 'summer' if (x >= 6) & (x <= 8)
        else 'fall' if (x >= 9) & (x <= 11)
        else 'NA'
    )

    # seleciona só as colunas necessárias
    df = df[['id', 'date', 'price', 'bedrooms', 'bathrooms', 'm2_living',
           'm2_lot', 'floors', 'waterfront', 'condition_type', 'season',
           'has_basement', 'm2_basement', 'yr_built', 'yr_renovated', 'zipcode',
           'price_mean_by_zipcode', 'lat', 'lon']]

    return df

def calculate_percentage_change(col2,col1):
    if (col1 == 0):
        return 100

    return ((col2 - col1) / col1) * 100

def print_percentage_change(condition, label1, label2, percentage):
    return st.subheader(
        'Imóveis {} são '.format(condition)
        + ('{:0.2f}% {}'.format(percentage, label1) if percentage >= 0
           else '{:0.2f}% {}'.format(percentage * -1, label2))
        + ' em média'
    )

def recommendation_tables(df):
    # sugere casas em boas condições, com vista para a água e abaixo do preço da região
    df['buy'] = df.apply(
        lambda x:
        'yes' if (x['condition_type'] == 'good')
        & (x['waterfront'] == 'yes')
        & (x['price'] < x['price_mean_by_zipcode'])
        else 'no',
        axis=1
    )

    # cria uma coluna com a média do preço da região e da sazonalidade de cada casa
    df['price_mean_by_zipcode_and_season'] = df[['price', 'zipcode', 'season']].groupby(
        ['zipcode', 'season']).transform('mean')

    # calcula o preço de venda para cada casa
    df['sell_price'] = df.apply(
        lambda x:
        x['price'] + 0.3 * x['price'] if x['price'] < x['price_mean_by_zipcode_and_season']
        else x['price'] + 0.1 * x['price'],
        axis=1
    )

    # calcula o lucro para a venda de cada casa
    df['profit'] = df['sell_price'] - df['price']

    st.header('Lucro estimado de {}'.format(locale.currency(df.loc[df['buy'] == 'yes', 'profit'].sum(), grouping=True)))

    st.subheader('Recomendações de compra')
    st.dataframe(df.loc[df['buy'] == 'yes', ['id', 'price', 'zipcode', 'lat', 'lon', 'season']].reset_index(drop=True))

    st.subheader('Recomendações de venda')
    st.dataframe(df.loc[:, ['id', 'sell_price', 'zipcode', 'lat', 'lon', 'season']])

    st.subheader('Localização das casas')
    st.map(df)

    return None

def hypothesis_tables(df):
    # ==========
    # Hypotese 1 - Imóveis que possuem vista para água, são 30% mais caros, na média.
    # ==========

    mean_waterfront_yes = stats.trim_mean(df.loc[df['waterfront'] == 'yes', 'price'], 0.1)

    mean_waterfront_no = stats.trim_mean(df.loc[df['waterfront'] == 'no', 'price'], 0.1)

    print_percentage_change(
        'com vista para a água',
        'mais caros',
        'mais baratos',
        calculate_percentage_change(mean_waterfront_yes, mean_waterfront_no)
    )

    fig = plt.figure(figsize=(10, 4))
    has_waterfront = sns.violinplot(x='waterfront', y='price', data=df, order=['yes', 'no'], inner='quartile')
    has_waterfront.set(xticklabels=['sim', 'não'])
    has_waterfront.set(xlabel='vista para a água', ylabel='preço')
    plt.ticklabel_format(style='plain', axis='y')
    st.pyplot(fig)

    # ==========
    # Hypotese 2 - Imóveis com data de construção menor que 1955, são 50% mais baratos, na média.
    # ==========

    mean_construction_before = stats.trim_mean(df.loc[df['yr_built'] < 1955, 'price'], 0.1)

    mean_construction_after = stats.trim_mean(df.loc[df['yr_built'] >= 1955, 'price'], 0.1)

    print_percentage_change(
        'construídos antes de 1955',
        'mais caros',
        'mais baratos',
        calculate_percentage_change(mean_construction_before, mean_construction_after)
    )

    # Create a column that tells whether the house was built before 1955
    df.loc[df['yr_built'] < 1955, 'built_before_1955'] = 'yes'
    df.loc[df['yr_built'] >= 1955, 'built_before_1955'] = 'no'

    fig = plt.figure(figsize=(10, 4))
    built_before_1955 = sns.barplot(x='built_before_1955', y='price', data=df, order=['yes', 'no'])
    built_before_1955.set(xticklabels=['construído antes de 1955', 'construído depois de 1955'])
    built_before_1955.set(xlabel='ano de construção', ylabel='preço')
    st.pyplot(fig)

    # ==========
    # Hypotese 3 - Imóveis sem porão são 50% maiores do que com porão.
    # ==========

    mean_size_basement_no = stats.trim_mean(df.loc[df['m2_basement'] == 0, 'm2_lot'], 0.1)

    mean_size_basement_yes = stats.trim_mean(df.loc[df['m2_basement'] > 0, 'm2_lot'], 0.1)

    print_percentage_change(
        'sem porão',
        'maiores',
        'menores',
        calculate_percentage_change(mean_size_basement_no, mean_size_basement_yes)
    )

    fig = plt.figure(figsize=(10, 4))
    built_before_1955 = sns.barplot(x='m2_lot', y='has_basement', data=df)
    built_before_1955.set(yticklabels=['com porão', 'sem porão'])
    built_before_1955.set(ylabel='', xlabel='tamanho da casa (m2)')
    st.pyplot(fig)

    # ==========
    # Hypotese 4 - O crescimento do preço dos imóveis YoY ( Year over Year ) é de 10%
    # ==========

    mean_price_2014 = stats.trim_mean(df.loc[df['yr_built'] == 2014, 'price'], 0.1)
    mean_price_2015 = stats.trim_mean(df.loc[df['yr_built'] == 2015, 'price'], 0.1)

    st.subheader(
        'O crescimento ano a ano dos imóveis de 2014 à 2015 foi de {:0.2f}%'
        .format(calculate_percentage_change(mean_price_2014, mean_price_2015))
    )

    fig = plt.figure(figsize=(10, 4))
    yoy = sns.lineplot(x='yr_built', y='price', data=df)
    yoy.set(xlabel='ano de construção', ylabel='preço')
    yoy.set(xlim=(2000,2020))
    yoy.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.ticklabel_format(style='plain', axis='y')
    st.pyplot(fig)

    # ==========
    # Hypotese 5 - Imóveis com 3 banheiros tem um crescimento MoM ( Month over Month ) de 15%
    # ==========

    mean_price_january_2015 = stats.trim_mean(
        df.loc[(df['bathrooms'] == 3)
        & (df['date'].dt.year == 2015)
        & (df['date'].dt.month == 1), 'price'],
        0.1
    )
    mean_price_february_2015 = stats.trim_mean(
        df.loc[(df['bathrooms'] == 3)
        & (df['date'].dt.year == 2015)
        & (df['date'].dt.month == 2), 'price'],
        0.1
    )

    st.subheader(
        'O crescimento mês a mês dos imóveis de janeiro de 2015 à fevereiro de 2015 foi de {:0.2f}%'
        .format(calculate_percentage_change(mean_price_january_2015, mean_price_february_2015))
    )

    df['month'] = df['date'].dt.month

    fig = plt.figure(figsize=(10, 4))
    mom = sns.lineplot(
        x='month',
        y='price',
        data=df.loc[(df['bathrooms'] == 3) & (df['date'].dt.year == 2015), ['month', 'price']],
    )
    mom.xaxis.set_major_locator(MaxNLocator(integer=True))
    mom.set(xticklabels=['janeiro', 'fevereiro', 'março', 'abril', 'maio'])
    mom.set(xlabel='mês', ylabel='preço')
    plt.ticklabel_format(style='plain', axis='y')
    st.pyplot(fig)

    # ==========
    # Hypotese 6 - Imóveis com porão são 20% mais caros em média
    # ==========

    mean_price_basement_no = stats.trim_mean(df.loc[df['m2_basement'] == 0, 'price'], 0.1)

    mean_price_basement_yes = stats.trim_mean(df.loc[df['m2_basement'] > 0, 'price'], 0.1)

    print_percentage_change(
        'com porão',
        'mais caros',
        'mais baratos',
        calculate_percentage_change(mean_price_basement_yes, mean_price_basement_no)
    )

    fig = plt.figure(figsize=(10, 4))
    built_before_1955 = sns.barplot(x='price', y='has_basement', data=df)
    built_before_1955.set(yticklabels=['com porão', 'sem porão'])
    built_before_1955.set(ylabel='', xlabel='preço')
    st.pyplot(fig)

    # ==========
    # Hypotese 7 - Mais de 80% de imóveis com data de construção anterior à 2005 não estão em boas condições
    # ==========

    count_condition = df['condition_type'].value_counts()
    count_condition_not_good = count_condition.sum() - count_condition['good']

    st.subheader(
        '{:0.2f}% dos imóveis construídos antes de 2005 não estão em boas condições'
        .format(count_condition_not_good*100/count_condition.sum() if count_condition.sum() != 0 else 0)
    )

    fig = plt.figure(figsize=(10, 4))
    colors = sns.color_palette('pastel')
    plt.pie(
        [count_condition['bad'], count_condition['good'], count_condition['regular']],
        labels=['ruim', 'bom', 'regular'],
        colors=colors
    )
    st.pyplot(fig)

    # ==========
    # Hypotese 8 - Imóveis vendidos durante o inverno são 10% mais baratos em média
    # ==========

    mean_price_winter = stats.trim_mean(df.loc[df['season'] == 'winter', 'price'], 0.1)
    mean_price_no_winter = stats.trim_mean(df.loc[df['season'] != 'winter', 'price'], 0.1)

    mean_price_spring = stats.trim_mean(df.loc[df['season'] == 'spring', 'price'], 0.1)
    mean_price_summer = stats.trim_mean(df.loc[df['season'] == 'summer', 'price'], 0.1)
    mean_price_fall = stats.trim_mean(df.loc[df['season'] == 'fall', 'price'], 0.1)

    print_percentage_change(
        'vendidos durante o inverno',
        'mais caros',
        'mais baratos',
        calculate_percentage_change(mean_price_winter, mean_price_no_winter)
    )

    fig = plt.figure(figsize=(10, 4))
    sns.barplot(
        x=[mean_price_winter, mean_price_spring, mean_price_summer, mean_price_fall],
        y=['inverno', 'primavera', 'verão', 'outono']
    )
    st.pyplot(fig)

    # ==========
    # Hypotese 9 - 70% dos imóveis com vista para a água não tem porão
    # ==========

    waterfront_no_basement = len(df.loc[(df['waterfront'] == 'yes') & (df['m2_basement'] == 0), 'id'])
    waterfront = len(df.loc[df['waterfront'] == 'yes', 'id'])

    st.subheader(
        '{:0.2f}% dos imóveis com vista para a água não tem porão'
        .format((waterfront_no_basement*100/waterfront) if waterfront != 0 else 0)
    )

    st.dataframe(pd.crosstab(
        index=(df['waterfront'].apply(lambda x: 'Com vista para a água' if x == 'yes' else 'Sem vista para a água')),
        columns=df['has_basement'].apply(lambda x: 'Com porão' if x == 'yes' else 'Sem porão'))
    )

    # ==========
    # Hypotese 10 - Imóveis renovados depois de 2012 (a menos de 3 anos) são 10% mais caros do que a media
    # ==========

    mean_price_renovated_before = stats.trim_mean(df.loc[df['yr_renovated'] <= 2012, 'price'], 0.1)
    mean_price_renovated_after = stats.trim_mean(df.loc[df['yr_renovated'] > 2012, 'price'], 0.1)

    print_percentage_change(
        'renovados depois de 2012',
        'mais caros',
        'mais baratos',
        calculate_percentage_change(mean_price_renovated_after, mean_price_renovated_before)
    )

    # Create a column that tells whether the house was built before 1955
    df.loc[df['yr_renovated'] < 1955, 'renovated_before_2012'] = 'yes'
    df.loc[df['yr_renovated'] >= 1955, 'renovated_before_2012'] = 'no'

    fig = plt.figure(figsize=(10, 4))
    renovated_after_2012 = sns.barplot(x='renovated_before_2012', y='price', data=df, order=['yes', 'no'])
    renovated_after_2012.set(xticklabels=['renovado antes de 2012', 'renovado depois de 2012'])
    renovated_after_2012.set(xlabel='ano de renovação', ylabel='preço')
    st.pyplot(fig)

    # ==========
    # Hypotese 11 - Imóveis com 2 ou mais andares são 20% mais caros do que a média
    # ==========

    mean_price_one_floor = stats.trim_mean(df.loc[df['floors'] == 1, 'price'], 0.1)
    mean_price_several_floors = stats.trim_mean(df.loc[df['floors'] >= 2, 'price'], 0.1)

    print_percentage_change(
        'com dois ou mais andares',
        'mais caros',
        'mais baratos',
        calculate_percentage_change(mean_price_several_floors, mean_price_one_floor)
    )

    # Create a column that tells whether the house was built before 1955
    df.loc[df['floors'] == 1, 'one_floor'] = 'yes'
    df.loc[df['floors'] >= 2, 'one_floor'] = 'no'

    fig = plt.figure(figsize=(10, 4))
    built_before_1955 = sns.barplot(x='price', y='one_floor', data=df, order=['yes', 'no'])
    built_before_1955.set(yticklabels=['um andar', 'mais de um andar'])
    built_before_1955.set(xlabel='preço', ylabel='número de andares')
    st.pyplot(fig)

    # ==========
    # Hypotese 12 -80% dos imoveis com mais de 50m2 na sala de estar tem preço acima da média da região
    # ==========

    qnt_big_living = df.loc[df['m2_living'] > 50, 'id'].count()
    qnt_big_living_high_price = df.loc[(df['m2_living'] > 50) & (df['price'] > df['price_mean_by_zipcode']), 'id'].count()
    qnt_big_living_low_price = df.loc[(df['m2_living'] > 50) & (df['price'] <= df['price_mean_by_zipcode']), 'id'].count()

    st.subheader(
        '{:0.2f}% dos imóveis com mais de 50 metros quadrados na sala de estar tem preço acima da média da região'
        .format(qnt_big_living_high_price*100/qnt_big_living if qnt_big_living != 0 else 0)
    )

    fig = plt.figure(figsize=(10, 4))
    colors = sns.color_palette('pastel')
    plt.pie(
        [qnt_big_living_high_price, qnt_big_living_low_price],
        labels=['acima da média', 'abaixo da média'],
        colors=colors
    )
    st.pyplot(fig)

    return None


if __name__ == '__main__':
    # ETL
    path = 'datasets/kc_house_data.csv'

    df = get_data(path)
    df = treat_data(df)

    recommendation_tables(df)
    hypothesis_tables(df)