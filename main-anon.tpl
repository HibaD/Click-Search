<!DOCTYPE html>
<html lang="en">

 <head>
 	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Click Search</title>
	<!-- Latest compiled and minified CSS -->
	<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
 </head>

 <body>
	<nav class="navbar navbar-light">
		<div class="container">
			<form method="GET" action="/">
				<img class="logo" src="https://images.techhive.com/images/article/2015/10/mouse-click-stock-100622925-large.jpg"/>
				<input class="form-control searchBar" type="text" name="keywords"></input>
			</form>
			
			<div class="login">
				<form method="GET" action="/">
					<input type="Submit" class="btn btn-default" name="Login" value="Login"></input>
					<h6>Logged in as {{email}}</h6>
				</form>
			</div>
		</div>
	</nav>
	<br>
	<div class="container">
		% if resnum > 0:
			<div class="pages col-sm-8">
				<table id="results" name="results" class="table table-hover table-responsive">
					<tr>
						<h2>Search Results</h2>
						<h6>Returned {{resnum}} result(s) for '{{wordsearched}}'</h6>
					</tr>

					% for url, title in wordresult:
					<tr>
						<td><h4>{{title}}</h4>
						<a href={{url}}>{{url}}</a>
						</td>
					</tr>
					% end
				</table>
			
				<form method="GET" action="/">
				<div class="form-group">
					% if page > 0:
					<input type="Submit" class="btn btn-default" name="Prev" value="Previous"></input>
					% end
					% if resnum > (page+5):
					<input type="Submit" class="btn btn-default" name="Next" value="Next"></input>
					% end
				</div>
				</form>
			</div>
			% if len(suggestions) > 0:
			<div class="suggestions col-sm-3">
				<h3>See Results About</h3>
				<div id="suggestions" name="suggestions">
					% for word in suggestions:
					<form method="GET" action="/">
						<input id="link" type="Submit" class="btn btn-link" name="autovalue" value = "{{word}}"></input>
					</form>
					%end
				</div>
			</div>
			% end
		% end
	
		% if page == 0 and resnum == 0:
			<h2>No Results</h2>
		% end
	</div>
	
	% if auto: 
	<div class="container">
		<form method="GET" action="/">
			<span>Did you mean "<input type="Submit" class="btn btn-link" name="autovalue" value = "{{word}}"></input>"?</span>
		</form>
					
	</div>
	% end
 </body>

</html>
