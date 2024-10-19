import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
 
function SearchBar() {
  // test
  return (
    <div className="flex w-full max-w-sm items-center space-x-2">
      <Input type="search" placeholder="Enter a Location" className="homebase-input"/>
      <Button type="submit">Search</Button>
    </div>
  )
}

export default SearchBar;