import pandas as pd
import numpy as np

invHeader = pd.read_csv("invoices_header.csv", sep=";")
invProducts = pd.read_csv("invoices_products.csv", sep=";")
products = pd.read_csv("products.csv", sep=";")
suppliers = pd.read_csv("suppliers.csv", sep=";")
currency = pd.read_csv("daily_currencies.csv", sep=";")

invHeader["InboundDate"] = pd.to_datetime(invHeader["InboundDate"])
invHeader["InvoiceDate"] = pd.to_datetime(invHeader["InvoiceDate"])
invHeader["OrderDate"] =  pd.to_datetime(invHeader["OrderDate"])
currency["Date"] = pd.to_datetime(currency["Date"])


#Devuelve los totales de cada envio
def totalsPerSection():
    totals = []
    exchange = 0
    """
    Por cada una de las transacciones miramos si el cambio en es euros,
    de ser así, el cambio es 1, sino, miramos cual es el cambio en el dia de la
    factura, el try/catch está ahi porque hay fechas de factura que no figuran
    en el dataframe de currencies
    """
    for index, invoice in invHeader.iterrows():
        if(suppliers[suppliers["IDSupplier"] == invoice["Supplier"]]["Currency"].values[0] == "EUR"):
            exchange = 1
        else:
            try:
                exchange = currency[currency["Date"] == invoice["InvoiceDate"]]["Open"].values[0]     
            except:
                exchange = 0
        #Luego para cada pedido se calcula el total con el cambio adecuado en una nueva columna
        for index1, product in invProducts[invProducts["Invoice"] == invoice["Invoice"]].iterrows():
            newRow = product.values.tolist()
            newRow.append(product["Quantity"] * (product["PurchasePrice (Unit)"] * exchange))
            totals.append(newRow)
    return pd.DataFrame(totals, columns=np.append(invProducts.columns.values, "Total"))


#Devuelve el dataframe con la informacion del lead time real de cada envio
def leadTimePerProviderProductYear():
    actualLeadTime = []
    year = []
    month = []
    dfCopy = invHeader.copy()
    #Para cada pedido se calcula el leadtime real basado en su localizacion
    for index, invoice in invHeader.iterrows():
        if (suppliers[suppliers["IDSupplier"] == invoice["Supplier"]]["Currency"].values[0] == "EUR"):
            if (suppliers[suppliers["IDSupplier"] == invoice["Supplier"]]["Country"].values[0] == "ES"):
                actualLeadTime.append((invoice["InboundDate"] - invoice["OrderDate"]).days -  10)
            else:
                actualLeadTime.append((invoice["InboundDate"] - invoice["OrderDate"]).days -  20)
        else:
            actualLeadTime.append((invoice["InboundDate"] - invoice["OrderDate"]).days -  45)
        year.append(invoice["InboundDate"].year)
        month.append(invoice["InboundDate"].month)
    #Las nuevas columnas son para agrupar por año en el caso de este apartado de proveedores y la de mes para la parte opcional
    dfCopy["Lead Time"] = actualLeadTime
    dfCopy["Year"] = year
    dfCopy["Month"] = month
    join = dfCopy.join(invProducts.set_index('Invoice'), on = "Invoice")
    return join


#Devuelve la comparacion del presupuesto con los gastado realmente
def budgetAgainstActual(perMonth):
    #Este diccionario se usa para mapear los meses del excel a números
    dictMeses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
                 "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
    #Las siguientes lineas limpian el dataframe de los espacios en blanco y nombran las columnas
    exc = pd.read_excel("purchase_budget.xls")
    firstRow = exc.first_valid_index()
    firstColumn = exc.columns.values.tolist().index(exc.transpose().first_valid_index())
    exc.columns = exc.iloc[firstRow]
    exc = exc.iloc[firstRow+1:, firstColumn:]
    exc.reset_index(drop = True)
    exc["Mes"] = exc["Mes"].map(dictMeses)
    exc = exc.infer_objects()
    exc.columns = ['Year', 'Month', 'Seccion A', 'Seccion B', 'Seccion C', 'Seccion D',
           'Seccion E', 'Seccion F']
    timeFrame = pd.DataFrame(perMonth.reset_index())
    #Para cada una de las secciones se filtra el dataframe y se añade el valor real obtenido en el primer apartado
    for section in timeFrame["Section"].unique():
        sec = timeFrame[timeFrame["Section"] == section]
        sec.columns = ["Year", "Month", "Section", "Real " + section]
        exc = exc.merge(sec.drop("Section", axis = 1), on = ["Year", "Month"])
    return exc



if __name__ == "__main__":
    #Las compras realizadas diariamente por secccion
    totals = totalsPerSection()
    #El join es para tener la fecha y poder agrupar diariamente
    dailyPurchases = totals.join(invHeader.set_index("Invoice"), on = "Invoice")
    dailyPurchases = dailyPurchases.groupby(["Section", "InvoiceDate"])["Total"].sum()
    dailyPurchases.reset_index().to_csv("dailyPurchases.csv", index = False)
    #Parte proveedores
    perProvider = leadTimePerProviderProductYear()
    perProvider["Totals"] = totals["Total"] 
    #Primera metrica
    numberSupplierProductPerYear = perProvider.groupby(["Supplier", "Year"])["Product"].count()
    amountSupplierPerYear = perProvider.groupby(["Supplier", "Year"])["Totals"].sum()
    amountSupplierPerYear = amountSupplierPerYear.reset_index()
    amountSupplierPerYear["Amount bought"] = numberSupplierProductPerYear.values
    amountSupplierPerYear.to_csv("amountAndProductPerYear.csv", index = False)
    #Segunda metrica
    leadTimePerProviderProductYearMean = perProvider.groupby(["Supplier", "Product", "Year"])["Lead Time"].mean()
    leadTimePerProviderProductYearMean.reset_index().to_csv("leadTimePerProviderProductYearMean.csv", index = False)
    #Parte opcional
    perMonth = perProvider.groupby(["Year", "Month", "Section"])["Totals"].sum()
    budgetAndRealComparison = budgetAgainstActual(perMonth)
    budgetAndRealComparison.to_csv("budgetAndRealComparison.csv", index = False)
    
                
            
        